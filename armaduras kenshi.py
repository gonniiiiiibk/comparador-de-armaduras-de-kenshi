"""
Analizador de Armaduras de Kenshi.

Calcula tres índices por armadura:
    - armor_index:  protección efectiva (resistencias × cobertura)
    - debuff_index: costo total en habilidades penalizadas
    - bonus_index:  valor normalizado de las bonificaciones

Uso:
    python main.py
"""

# Importa la base de datos y las constantes desde armor_db.py.
from armor_db import (
    ARMADURAS_DB, PARTES_CUERPO, ETIQUETAS,
    STATS_PENALIZABLES, STATS_BONIFICABLES,
)


# ------------------------------------------------------------
#   UTILIDADES DE ENTRADA
#   Funciones auxiliares para pedir datos al usuario con validación.
# ------------------------------------------------------------

def pedir_float(mensaje, minimo=0.0, maximo=1.0, permitir_vacio=False):
    """
    Pide un número decimal al usuario, validando rango y formato.

    Args:
        mensaje (str): Texto que se muestra al pedir el valor.
        minimo (float): Valor mínimo aceptado (por defecto 0.0).
        maximo (float): Valor máximo aceptado (por defecto 1.0).
        permitir_vacio (bool): Si True, acepta Enter vacío y devuelve None.

    Returns:
        float | None: El número ingresado, o None si se permitió vacío.

    Acepta tanto coma como punto como separador decimal.
    Reintenta hasta que el usuario ingrese un valor válido.
    """
    while True:
        valor = input(mensaje).strip().replace(",", ".")
        if valor == "" and permitir_vacio:
            return None
        try:
            num = float(valor)
        except ValueError:
            print("  ⚠  Ingresa un número válido (ej: 0.75).")
            continue
        if num < minimo or num > maximo:
            print(f"  ⚠  El valor debe estar entre {minimo} y {maximo}.")
            continue
        return num


def pedir_texto(mensaje):
    """
    Pide una cadena de texto no vacía al usuario.

    Args:
        mensaje (str): Texto que se muestra al pedir el valor.

    Returns:
        str: El texto ingresado (ya sin espacios en los extremos).

    Reintenta hasta que el usuario ingrese algo distinto de vacío.
    """
    while True:
        txt = input(mensaje).strip()
        if txt:
            return txt
        print("  ⚠  Este campo no puede estar vacío.")


def pedir_si_no(mensaje):
    """
    Pide una respuesta de sí/no al usuario.

    Args:
        mensaje (str): Texto que se muestra al pedir la respuesta.

    Returns:
        bool: True si respondió sí (s/si/sí/y/yes), False si respondió no.

    Acepta variantes en español e inglés. Reintenta si la respuesta no es válida.
    """
    while True:
        r = input(mensaje).strip().lower()
        if r in ("s", "si", "sí", "y", "yes"):
            return True
        if r in ("n", "no"):
            return False
        print("  ⚠  Responde 's' o 'n'.")


# ------------------------------------------------------------
#   CÁLCULO
#   Función central que convierte los datos crudos en índices.
# ------------------------------------------------------------

def evaluar_armadura(cut_res, blunt_res, harpoon_res, body_coverage,
                     penalizaciones, bonificaciones):
    """
    Calcula los tres índices de una armadura a partir de sus datos crudos.

    Args:
        cut_res (float): Resistencia a cortes (0-1).
        blunt_res (float): Resistencia a contundente (0-1).
        harpoon_res (float): Resistencia a arpones (0-1).
        body_coverage (dict): Cobertura por parte del cuerpo {parte: 0-1}.
        penalizaciones (dict): {stat: multiplicador (0-1)}.
        bonificaciones (dict): {stat: valor}. Multiplicador si >1, suma plana si ≤1.

    Returns:
        dict: Con las claves:
            - armor_index: protección efectiva (resistencias × cobertura)
            - debuff_index: suma de reducciones porcentuales
            - bonus_index: valor normalizado de los bonus
            - cobertura_promedio: cobertura media de las partes protegidas
            - promedio_resistencias: media de las tres resistencias

    Lógica:
        armor_index  = promedio_resistencias × cobertura_promedio
        debuff_index = Σ (1 - multiplicador) para cada penalización
        bonus_index  = Σ aportes normalizados (mult→valor-1, plano→valor/10)
    """
    # Cobertura promedio: media de las partes protegidas.
    # Si no hay partes protegidas, la cobertura es 0.
    if body_coverage:
        cobertura_promedio = sum(body_coverage.values()) / len(body_coverage)
    else:
        cobertura_promedio = 0.0

    # Promedio simple de las tres resistencias.
    promedio_resistencias = (cut_res + blunt_res + harpoon_res) / 3

    # Índice de armadura: interacción entre resistencia y cobertura.
    armor_index = promedio_resistencias * cobertura_promedio

    # Índice de debuff: suma de reducciones porcentuales.
    # Se fuerza a 0 si por algún motivo diera negativo.
    debuff_index = sum(1.0 - mult for mult in penalizaciones.values())
    debuff_index = max(0.0, debuff_index)

    # Índice de bonus: normaliza multiplicadores y sumas planas.
    bonus_total = 0.0
    for val in bonificaciones.values():
        if val > 1.0:
            # Es un multiplicador: su aporte es el exceso sobre 1.
            bonus_total += (val - 1.0)
        else:
            # Es una suma plana: se divide por 10 para hacerla comparable.
            bonus_total += val / 10.0

    # Devuelve los índices redondeados junto con datos intermedios.
    return {
        "armor_index":          round(armor_index, 4),
        "debuff_index":         round(debuff_index, 4),
        "bonus_index":          round(bonus_total, 4),
        "cobertura_promedio":   round(cobertura_promedio, 4),
        "promedio_resistencias": round(promedio_resistencias, 4),
    }


# ------------------------------------------------------------
#   COMPARATIVA AUTOMÁTICA
#   Recorre la base de datos, calcula los índices y muestra la tabla.
# ------------------------------------------------------------

def comparar_todas_las_armaduras():
    """
    Calcula y muestra la comparativa de todas las armaduras de ARMADURAS_DB.

    Flujo:
        1. Itera sobre cada armadura y llama a evaluar_armadura().
        2. Enriquece el resultado con nombre, slot y clase.
        3. Ordena por armor_index descendente.
        4. Imprime la tabla completa.
        5. Calcula y muestra rankings especiales:
           - Mejor equilibrio (armor - debuff + bonus)
           - Top 3 por índice de armadura puro
           - Top 3 por índice de bonus
    """
    print("\n" + "=" * 100)
    print("  COMPARATIVA TOTAL DE ARMADURAS (Base de Datos - Grado Masterwork)")
    print("=" * 100)

    # Lista donde se acumulan los resultados de cada armadura.
    resultados = []
    for nombre, datos in ARMADURAS_DB.items():
        # Calcula los índices de la armadura actual.
        res = evaluar_armadura(
            cut_res=datos["cut_res"],
            blunt_res=datos["blunt_res"],
            harpoon_res=datos["harpoon_res"],
            body_coverage=datos["cobertura"],
            penalizaciones=datos["penalizaciones"],
            bonificaciones=datos["bonificaciones"],
        )
        # Añade metadatos para mostrarlos en la tabla.
        res["nombre"] = nombre
        res["slot"] = datos["slot"]
        res["clase"] = datos["clase"]
        resultados.append(res)

    # Ordena la lista por índice de armadura, de mayor a menor.
    resultados.sort(key=lambda x: x["armor_index"], reverse=True)

    # Cabecera de la tabla.
    print(f"\n  {'Armadura':<24} {'Slot':<9} {'Clase':<8} "
          f"{'ArmorIdx':>10} {'DebuffIdx':>11} {'BonusIdx':>10}")
    print("  " + "-" * 96)

    # Cuerpo de la tabla: una fila por armadura.
    for r in resultados:
        print(f"  {r['nombre']:<24} {r['slot']:<9} {r['clase']:<8} "
              f"{r['armor_index']:>10.4f} {r['debuff_index']:>11.4f} "
              f"{r['bonus_index']:>10.4f}")
    print("=" * 100)

    # Ranking: mejor equilibrio (armor - debuff + bonus).
    mejor = max(resultados,
                key=lambda x: x["armor_index"] - x["debuff_index"] + x["bonus_index"])
    print(f"\n  🏆 Mejor equilibrio (Armor - Debuff + Bonus): {mejor['nombre']}")
    print(f"     ArmorIdx={mejor['armor_index']:.4f} | "
          f"DebuffIdx={mejor['debuff_index']:.4f} | "
          f"BonusIdx={mejor['bonus_index']:.4f}")

    # Ranking: top 3 por índice de armadura puro.
    print("\n  🛡️  Top 3 por Índice de Armadura puro:")
    for i, r in enumerate(resultados[:3], 1):
        print(f"     {i}. {r['nombre']} ({r['slot']}) → {r['armor_index']:.4f}")

    # Ranking: top 3 por índice de bonus.
    top_bonus = sorted(resultados, key=lambda x: x["bonus_index"], reverse=True)[:3]
    print("\n  ✨ Top 3 por Índice de Bonus:")
    for i, r in enumerate(top_bonus, 1):
        print(f"     {i}. {r['nombre']} ({r['slot']}) → {r['bonus_index']:.4f}")


# ------------------------------------------------------------
#   INGRESO MANUAL
#   Permite al usuario cargar una armadura fuera de la base de datos.
# ------------------------------------------------------------

def ingresar_armadura():
    """
    Guía al usuario para ingresar los datos de una armadura manualmente.

    Returns:
        dict: Datos de la armadura (resistencias, cobertura, penalizaciones,
              bonificaciones) junto con los tres índices calculados.

    El flujo es:
        1. Pedir nombre.
        2. Pedir las tres resistencias.
        3. Pedir la cobertura de cada parte del cuerpo.
        4. Pedir penalizaciones (solo se guardan las que tengan mult < 1).
        5. Pedir bonificaciones (solo se guardan las que sean ≠ 0).
        6. Llamar a evaluar_armadura() y devolver todo junto.
    """
    print("\n" + "=" * 55)
    print("  INGRESO MANUAL DE ARMADURA")
    print("=" * 55)

    # Nombre de la armadura.
    nombre = pedir_texto("Nombre: ")

    # Resistencias (0 a 1).
    print("\n-- Resistencias (0.0 a 1.0) --")
    cut_res = pedir_float("  Resistencia a CORTES:       ")
    blunt_res = pedir_float("  Resistencia a CONTUNDENTE: ")
    harpoon_res = pedir_float("  Resistencia a ARPONES:     ")

    # Cobertura por parte del cuerpo (vacío = 0).
    print("\n-- Cobertura por parte (0.0 a 1.0, vacío = 0) --")
    cobertura = {}
    for parte in PARTES_CUERPO:
        val = pedir_float(f"  {ETIQUETAS[parte]:<18}: ", permitir_vacio=True)
        cobertura[parte] = val if val is not None else 0.0

    # Penalizaciones: solo se guardan las que reduzcan la stat (mult < 1).
    print("\n-- PENALIZACIONES (multiplicador 0-1, vacío = sin penalización) --")
    penalizaciones = {}
    for stat in STATS_PENALIZABLES:
        val = pedir_float(f"  {stat:<22}: ", permitir_vacio=True)
        if val is not None and val < 1.0:
            penalizaciones[stat] = val

    # Bonificaciones: solo se guardan las distintas de 0.
    print("\n-- BONIFICACIONES (mult >1 o suma plana, vacío = sin bonus) --")
    bonificaciones = {}
    for stat in STATS_BONIFICABLES:
        val = pedir_float(f"  {stat:<22}: ", minimo=0.0, maximo=100.0,
                          permitir_vacio=True)
        if val is not None and val != 0:
            bonificaciones[stat] = val

    # Calcula los índices con los datos ingresados.
    resultado = evaluar_armadura(cut_res, blunt_res, harpoon_res,
                                 cobertura, penalizaciones, bonificaciones)

    # Devuelve todo junto en un solo diccionario.
    return {
        "nombre": nombre,
        "cut_res": cut_res, "blunt_res": blunt_res, "harpoon_res": harpoon_res,
        "cobertura": cobertura,
        "penalizaciones": penalizaciones,
        "bonificaciones": bonificaciones,
        **resultado,
    }


def mostrar_resultado(d):
    """
    Muestra el desglose completo de una sola armadura.

    Args:
        d (dict): Diccionario devuelto por ingresar_armadura().

    Imprime resistencias, cobertura, penalizaciones, bonificaciones
    y los tres índices finales en un recuadro.
    """
    print("\n" + "-" * 55)
    print(f"  RESULTADO: {d['nombre']}")
    print("-" * 55)

    # Resistencias en formato porcentual.
    print(f"\n  Resistencias: Corte {d['cut_res']*100:.1f}% | "
          f"Contundente {d['blunt_res']*100:.1f}% | "
          f"Arpones {d['harpoon_res']*100:.1f}%")

    # Cobertura: solo se muestran las partes con cobertura > 0.
    print("\n  Cobertura:")
    for parte, val in d["cobertura"].items():
        if val > 0:
            print(f"    {ETIQUETAS[parte]:<18}: {val*100:5.1f}%")

    # Penalizaciones: cada stat con su multiplicador y su % de reducción.
    if d["penalizaciones"]:
        print("\n  Penalizaciones:")
        for stat, mult in d["penalizaciones"].items():
            print(f"    {stat:<22}: {mult:.2f}x ({(1-mult)*100:.1f}% menos)")

    # Bonificaciones: multiplicadores o sumas planas según su valor.
    if d["bonificaciones"]:
        print("\n  Bonificaciones:")
        for stat, val in d["bonificaciones"].items():
            if val > 1.0:
                print(f"    {stat:<22}: {val:.2f}x (+{(val-1)*100:.1f}%)")
            else:
                print(f"    {stat:<22}: +{val:g}")

    # Recuadro final con los tres índices.
    print("\n  ╔══════════════════════════════════════════╗")
    print(f"  ║  ÍNDICE DE ARMADURA: {d['armor_index']:.4f}  ({d['armor_index']*100:.1f}%)  ║")
    print(f"  ║  ÍNDICE DE DEBUFF:   {d['debuff_index']:.4f}  ({d['debuff_index']*100:.1f}%)  ║")
    print(f"  ║  ÍNDICE DE BONUS:    {d['bonus_index']:.4f}                  ║")
    print("  ╚══════════════════════════════════════════╝")


def comparar_manuales(armaduras):
    """
    Muestra una tabla comparativa de las armaduras ingresadas manualmente.

    Args:
        armaduras (list[dict]): Lista de diccionarios devueltos por
                                ingresar_armadura().

    Ordena por índice de armadura descendente antes de imprimir.
    """
    print("\n" + "=" * 85)
    print("  COMPARACIÓN DE ARMADURAS INGRESADAS MANUALMENTE")
    print("=" * 85)
    print(f"  {'Armadura':<24} {'ArmorIdx':>10} {'DebuffIdx':>12} {'BonusIdx':>10}")
    print("  " + "-" * 81)
    for d in sorted(armaduras, key=lambda x: x["armor_index"], reverse=True):
        print(f"  {d['nombre']:<24} {d['armor_index']:>10.4f} "
              f"{d['debuff_index']:>12.4f} {d['bonus_index']:>10.4f}")
    print("=" * 85)


# ------------------------------------------------------------
#   PROGRAMA PRINCIPAL
# ------------------------------------------------------------

def main():
    """
    Punto de entrada del programa.

    Flujo:
        1. Muestra un banner.
        2. Ejecuta la comparativa automática de toda la base de datos.
        3. Ofrece ingresar armaduras manualmente (opcional).
        4. Si se ingresaron dos o más, muestra la tabla comparativa.
    """
    print("╔═══════════════════════════════════════════════════╗")
    print("║   ANALIZADOR DE ARMADURAS DE KENSHI v4           ║")
    print("║   Base de datos integrada + comparativa total     ║")
    print("╚═══════════════════════════════════════════════════╝")

    # 1) Comparativa automática de toda la base de datos.
    comparar_todas_las_armaduras()

    # 2) Ingreso manual opcional.
    print("\n" + "-" * 100)
    if pedir_si_no("¿Querés ingresar armaduras manualmente para comparar? (s/n): "):
        armaduras = []
        while True:
            armaduras.append(ingresar_armadura())
            mostrar_resultado(armaduras[-1])
            if not pedir_si_no("\n¿Ingresar otra armadura? (s/n): "):
                break
        # Solo se muestra la tabla comparativa si hay más de una.
        if len(armaduras) > 1:
            comparar_manuales(armaduras)

    print("\n¡Listo! Gracias por usar el analizador. 🛡️\n")


# Punto de entrada: solo se ejecuta si el archivo se corre directamente.
if __name__ == "__main__":
    main()
    main()
