import re

def formatar_telefone(telefone):
    """
    Formata um número de telefone para o padrão (XX) XXXX-XXXX ou (XX) XXXXX-XXXX
    """
    if not telefone:
        return 'Não informado'
    
    # Remove tudo que não é número
    numeros = re.sub(r'\D', '', str(telefone))
    
    if len(numeros) == 0:
        return 'Não informado'
    
    # Se tiver 10 dígitos: (XX) XXXX-XXXX (telefone fixo)
    if len(numeros) == 10:
        return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:10]}"
    # Se tiver 11 dígitos: (XX) XXXXX-XXXX (celular com 9)
    elif len(numeros) == 11:
        return f"({numeros[:2]}) {numeros[2:7]}-{numeros[7:11]}"
    # Se tiver 8 dígitos: XXXX-XXXX (sem DDD)
    elif len(numeros) == 8:
        return f"{numeros[:4]}-{numeros[4:8]}"
    # Se tiver 9 dígitos: XXXXX-XXXX (sem DDD, com 9)
    elif len(numeros) == 9:
        return f"{numeros[:5]}-{numeros[5:9]}"
    # Caso contrário, retorna o número original
    else:
        return telefone