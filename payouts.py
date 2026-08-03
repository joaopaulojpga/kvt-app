# -*- coding: utf-8 -*-
"""
Cálculo do repasse financeiro aos instrutores.

Regra validada na planilha de controle (ver PRD, seção 4.3):
- Repasse = taxa fixa + (taxa por remador x MIN(remadores atribuídos, teto)).
- Cada instrutor atende até `limite_remadores_por_instrutor` (12) sozinho.
- Acima disso, o excedente é atribuído a um 2º instrutor, com a mesma fórmula.
- O repasse é calculado sobre inscritos/pagantes, independente de presença.
"""
from db import get_param


def repasse_por_instrutor(remadores_atribuidos: int) -> int:
    """Repasse (em centavos) para UM instrutor responsável por N remadores."""
    if remadores_atribuidos <= 0:
        return 0
    taxa_fixa = get_param("taxa_fixa_instrutor_centavos", 2500, int)
    taxa_remador = get_param("taxa_por_remador_centavos", 500, int)
    teto = get_param("teto_remadores_calculo", 10, int)
    return taxa_fixa + taxa_remador * min(remadores_atribuidos, teto)


def dividir_remadores_entre_instrutores(total_remadores: int) -> tuple[int, int]:
    """
    Divide o total de remadores da turma entre até 2 instrutores,
    seguindo a regra: o 1º assume até o limite (12), o 2º assume o
    excedente. Retorna (remadores_instrutor1, remadores_instrutor2).
    """
    limite = get_param("limite_remadores_por_instrutor", 12, int)
    instrutor1 = min(total_remadores, limite)
    instrutor2 = max(total_remadores - limite, 0)
    return instrutor1, instrutor2


def calcular_repasses_da_turma(total_remadores: int) -> dict:
    """
    Retorna o detalhamento completo do repasse de uma turma:
    {
        'remadores_instrutor1': int, 'repasse_instrutor1_centavos': int,
        'remadores_instrutor2': int, 'repasse_instrutor2_centavos': int,
        'total_repasse_centavos': int,
        'faturamento_bruto_centavos': int,
        'margem_liquida_centavos': int,
    }
    """
    r1, r2 = dividir_remadores_entre_instrutores(total_remadores)
    repasse1 = repasse_por_instrutor(r1)
    repasse2 = repasse_por_instrutor(r2)
    valor_aula = get_param("valor_aula_centavos", 3500, int)
    bruto = total_remadores * valor_aula
    total_repasse = repasse1 + repasse2
    return {
        "remadores_instrutor1": r1,
        "repasse_instrutor1_centavos": repasse1,
        "remadores_instrutor2": r2,
        "repasse_instrutor2_centavos": repasse2,
        "total_repasse_centavos": total_repasse,
        "faturamento_bruto_centavos": bruto,
        "margem_liquida_centavos": bruto - total_repasse,
    }
