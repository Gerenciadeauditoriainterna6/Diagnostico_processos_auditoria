# test_db.py
from logic import buscar_processos_detalhamento

print("🔍 Testando busca de processos para Detalhamento...")
processos = buscar_processos_detalhamento(area_id=1, auditoria_id=9)

print(f"\n📊 Total de processos encontrados: {len(processos)}")
for p in processos:
    print(f"  - {p['codigo_processo']}: {p['nome_processo']}")
    print(f"    Etapas: {len(p['etapas'])}")
    for e in p['etapas']:
        print(f"      - {e['codigo_etapa']}: {e['nome_etapa']} ({len(e['riscos'])} riscos)")