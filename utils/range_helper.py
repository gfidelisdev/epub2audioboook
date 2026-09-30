from typing import Optional, Set

def parse_page_range(range_str: Optional[str], total_paginas: Optional[int] = None) -> Optional[Set[int]]:
    """
    Interpreta uma string de range de páginas e retorna um conjunto com os números de páginas (1-indexados).
    Exemplos aceitos:
      - "5"         -> {5}
      - "1-10"      -> {1, 2, ..., 10}
      - "1-5,8,11-13" -> {1, 2, 3, 4, 5, 8, 11, 12, 13}
      - "10-"       -> páginas de 10 até total_paginas (ou erro se total desconhecido)
      - "-5"        -> páginas de 1 até 5
    """
    if not range_str or not range_str.strip():
        return None

    paginas: Set[int] = set()
    partes = [p.strip() for p in range_str.split(",") if p.strip()]

    for parte in partes:
        if "-" in parte:
            sub = parte.split("-", 1)
            inicio_str, fim_str = sub[0].strip(), sub[1].strip()
            
            inicio = int(inicio_str) if inicio_str else 1
            if fim_str:
                fim = int(fim_str)
            elif total_paginas is not None:
                fim = total_paginas
            else:
                raise ValueError(f"Fim do intervalo indefinido em '{parte}' e total de páginas não disponível.")

            if inicio > fim:
                raise ValueError(f"Intervalo inválido: {inicio} > {fim}")

            for p in range(inicio, fim + 1):
                paginas.add(p)
        else:
            paginas.add(int(parte))

    return paginas
