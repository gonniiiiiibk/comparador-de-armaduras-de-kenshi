

from armor_db import (
    ARMADURAS_DB, PARTES_CUERPO, ETIQUETAS,
    STATS_PENALIZABLES, STATS_BONIFICABLES,
)


def pedir_float(mensaje, minimo=0.0, maximo=1.0, permitir_vacio=False):

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

    while True:
        txt = input(mensaje).strip()
        if txt:
            return txt
        print("  ⚠  Este campo no puede estar vacío.")


def pedir_si_no(mensaje):

    while True:
        r = input(mensaje).strip().lower()
        if r in ("s", "si", "sí", "y", "yes"):
            return True
        if r in ("n", "no"):
            return False
        print("  ⚠  Responde 's' o 'n'.")


def evaluar_armadura(cut_res, blunt_res, harpoon_res, body_coverage,
                     penalizaciones, bonificaciones):


    if body_coverage:
        cobertura_promedio = sum(body_coverage.values()) / len(body_coverage)
    else:
        cobertura_promedio = 0.0


    promedio_resistencias = (cut_res + blunt_res + harpoon_res) / 3

    armor_index = promedio_resistencias * cobertura_promedio


    debuff_index = sum(1.0 - mult for mult in penalizaciones.values())
    debuff_index = max(0.0, debuff_index)


    bonus_total = 0.0
    for val in bonificaciones.values():
        if val > 1.0:

            bonus_total += (val - 1.0)
        else:

            bonus_total += val / 10.0


    return {
        "armor_index":          round(armor_index, 4),
        "debuff_index":         round(debuff_index, 4),
        "bonus_index":          round(bonus_total, 4),
        "cobertura_promedio":   round(cobertura_promedio, 4),
        "promedio_resistencias": round(promedio_resistencias, 4),
    }


def comparar_todas_las_armaduras():

    print("\n" + "=" * 100)
    print("  COMPARATIVA TOTAL DE ARMADURAS (Base de Datos - Grado Masterwork)")
    print("=" * 100)


    resultados = []
    for nombre, datos in ARMADURAS_DB.items():

        res = evaluar_armadura(
            cut_res=datos["cut_res"],
            blunt_res=datos["blunt_res"],
            harpoon_res=datos["harpoon_res"],
            body_coverage=datos["cobertura"],
            penalizaciones=datos["penalizaciones"],
            bonificaciones=datos["bonificaciones"],
        )

        res["nombre"] = nombre
        res["slot"] = datos["slot"]
        res["clase"] = datos["clase"]
        resultados.append(res)


    resultados.sort(key=lambda x: x["armor_index"], reverse=True)


    print(f"\n  {'Armadura':<24} {'Slot':<9} {'Clase':<8} "
          f"{'ArmorIdx':>10} {'DebuffIdx':>11} {'BonusIdx':>10}")
    print("  " + "-" * 96)


    for r in resultados:
        print(f"  {r['nombre']:<24} {r['slot']:<9} {r['clase']:<8} "
              f"{r['armor_index']:>10.4f} {r['debuff_index']:>11.4f} "
              f"{r['bonus_index']:>10.4f}")
    print("=" * 100)


    mejor = max(resultados,
                key=lambda x: x["armor_index"] - x["debuff_index"] + x["bonus_index"])
    print(f"\n  🏆 Mejor equilibrio (Armor - Debuff + Bonus): {mejor['nombre']}")
    print(f"     ArmorIdx={mejor['armor_index']:.4f} | "
          f"DebuffIdx={mejor['debuff_index']:.4f} | "
          f"BonusIdx={mejor['bonus_index']:.4f}")


    print("\n  🛡️  Top 3 por Índice de Armadura puro:")
    for i, r in enumerate(resultados[:3], 1):
        print(f"     {i}. {r['nombre']} ({r['slot']}) → {r['armor_index']:.4f}")


    top_bonus = sorted(resultados, key=lambda x: x["bonus_index"], reverse=True)[:3]
    print("\n  ✨ Top 3 por Índice de Bonus:")
    for i, r in enumerate(top_bonus, 1):
        print(f"     {i}. {r['nombre']} ({r['slot']}) → {r['bonus_index']:.4f}")


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


    nombre = pedir_texto("Nombre: ")


    print("\n-- Resistencias (0.0 a 1.0) --")
    cut_res = pedir_float("  Resistencia a CORTES:       ")
    blunt_res = pedir_float("  Resistencia a CONTUNDENTE: ")
    harpoon_res = pedir_float("  Resistencia a ARPONES:     ")


    print("\n-- Cobertura por parte (0.0 a 1.0, vacío = 0) --")
    cobertura = {}
    for parte in PARTES_CUERPO:
        val = pedir_float(f"  {ETIQUETAS[parte]:<18}: ", permitir_vacio=True)
        cobertura[parte] = val if val is not None else 0.0


    print("\n-- PENALIZACIONES (multiplicador 0-1, vacío = sin penalización) --")
    penalizaciones = {}
    for stat in STATS_PENALIZABLES:
        val = pedir_float(f"  {stat:<22}: ", permitir_vacio=True)
        if val is not None and val < 1.0:
            penalizaciones[stat] = val


    print("\n-- BONIFICACIONES (mult >1 o suma plana, vacío = sin bonus) --")
    bonificaciones = {}
    for stat in STATS_BONIFICABLES:
        val = pedir_float(f"  {stat:<22}: ", minimo=0.0, maximo=100.0,
                          permitir_vacio=True)
        if val is not None and val != 0:
            bonificaciones[stat] = val


    resultado = evaluar_armadura(cut_res, blunt_res, harpoon_res,
                                 cobertura, penalizaciones, bonificaciones)


    return {
        "nombre": nombre,
        "cut_res": cut_res, "blunt_res": blunt_res, "harpoon_res": harpoon_res,
        "cobertura": cobertura,
        "penalizaciones": penalizaciones,
        "bonificaciones": bonificaciones,
        **resultado,
    }


def mostrar_resultado(d):

    print("\n" + "-" * 55)
    print(f"  RESULTADO: {d['nombre']}")
    print("-" * 55)


    print(f"\n  Resistencias: Corte {d['cut_res']*100:.1f}% | "
          f"Contundente {d['blunt_res']*100:.1f}% | "
          f"Arpones {d['harpoon_res']*100:.1f}%")


    print("\n  Cobertura:")
    for parte, val in d["cobertura"].items():
        if val > 0:
            print(f"    {ETIQUETAS[parte]:<18}: {val*100:5.1f}%")


    if d["penalizaciones"]:
        print("\n  Penalizaciones:")
        for stat, mult in d["penalizaciones"].items():
            print(f"    {stat:<22}: {mult:.2f}x ({(1-mult)*100:.1f}% menos)")


    if d["bonificaciones"]:
        print("\n  Bonificaciones:")
        for stat, val in d["bonificaciones"].items():
            if val > 1.0:
                print(f"    {stat:<22}: {val:.2f}x (+{(val-1)*100:.1f}%)")
            else:
                print(f"    {stat:<22}: +{val:g}")


    print("\n  ╔══════════════════════════════════════════╗")
    print(f"  ║  ÍNDICE DE ARMADURA: {d['armor_index']:.4f}  ({d['armor_index']*100:.1f}%)  ║")
    print(f"  ║  ÍNDICE DE DEBUFF:   {d['debuff_index']:.4f}  ({d['debuff_index']*100:.1f}%)  ║")
    print(f"  ║  ÍNDICE DE BONUS:    {d['bonus_index']:.4f}                  ║")
    print("  ╚══════════════════════════════════════════╝")


def comparar_manuales(armaduras):

    print("\n" + "=" * 85)
    print("  COMPARACIÓN DE ARMADURAS INGRESADAS MANUALMENTE")
    print("=" * 85)
    print(f"  {'Armadura':<24} {'ArmorIdx':>10} {'DebuffIdx':>12} {'BonusIdx':>10}")
    print("  " + "-" * 81)
    for d in sorted(armaduras, key=lambda x: x["armor_index"], reverse=True):
        print(f"  {d['nombre']:<24} {d['armor_index']:>10.4f} "
              f"{d['debuff_index']:>12.4f} {d['bonus_index']:>10.4f}")
    print("=" * 85)




def main():

    print("╔═══════════════════════════════════════════════════╗")
    print("║   ANALIZADOR DE ARMADURAS DE KENSHI v4           ║")
    print("║   Base de datos integrada + comparativa total     ║")
    print("╚═══════════════════════════════════════════════════╝")


    comparar_todas_las_armaduras()


    print("\n" + "-" * 100)
    if pedir_si_no("¿Querés ingresar armaduras manualmente para comparar? (s/n): "):
        armaduras = []
        while True:
            armaduras.append(ingresar_armadura())
            mostrar_resultado(armaduras[-1])
            if not pedir_si_no("\n¿Ingresar otra armadura? (s/n): "):
                break

        if len(armaduras) > 1:
            comparar_manuales(armaduras)

    print("\n¡Listo! Gracias por usar el analizador. 🛡️\n")



if __name__ == "__main__":
    main()