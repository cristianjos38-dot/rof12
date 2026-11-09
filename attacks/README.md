# Corpus adversarial defensivo

`ATK-001.json` a `ATK-007.json` son vectores sintéticos de prueba generados
exclusivamente para el benchmark defensivo y las pruebas de resistencia del
`SecurityGate`. No representan incidentes reales ni contienen datos de
clientes. El corpus se ejecuta de forma idéntica contra el modo Baseline y el
modo Protected; las decisiones esperadas documentan la contención, no una
autorización operacional.

## Corpus v2

`v2_manifest.json` añade 18 fixtures sintéticos (ATK-V2-001 a ATK-V2-018) a
los siete vectores v1, para 25 casos documentados. Incluye inyección en varios
pasos, envenenamiento de salida de herramienta, homoglyphs Unicode, TOCTOU,
carrera de doble gasto, documentos sobredimensionados o malformados y PDFs con
capas contradictorias. Los veredictos esperados son terminales: `DENY` o
`QUARANTINE`; nunca se ejecuta una herramienta.
