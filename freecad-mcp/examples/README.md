# Ejemplos FreeCAD MCP — materiales e impresión

Ejemplos registrados en `examples.json` (ambos **aprobados**), con geometría,
métricas verificada y previews renderizadas. Unidades en mm.

---

## 1. Pierna transfemoral print-ready (rodilla de 4 barras)

- **Archivo**: `pierna_transfemoral.FCStd` — 11 objetos, 1 586 188 mm³ totales.
- **STL listos para slicer**: `stl/` (11 piezas, todas mallas cerradas/sólidas).
- **Verificación**: 13/13 pares de piezas sin interferencia (0.000 mm³);
  cinemática de la rodilla resuelta por IK con error de cierre 0.000 mm
  (demo a 0°, 15°, 30°, 45°).

### Materiales por pieza

| Pieza | Vol. (mm³) | Material recomendado | Notas de impresión |
|---|---:|---|---|
| `Socket_TF` | 469 863 | Resina térmica (uso clínico) / **PLA+ o PETG** (prototipo) | Pared 5 mm; boca arriba; el brim anterior (18°) puede llevar soporte |
| `Adaptador_TF` | 55 475 | **PETG** o ABS | Ya incluye los bolsillos de holgura de la rodilla |
| `Rodilla_Muslo` | 19 413 | **PETG** o nylon | Plataforma en cama: pernos horizontales quedan sin soporte |
| `Rodilla_Tibia` | 27 655 | **PETG** o nylon | Cruceta en cama, tallo vertical |
| `Barra_Ant` | 3 318 | **PETG** o nylon (ductilidad) | En canto; taladro Ø10.6 → desliza sobre perno Ø10 |
| `Barra_Pst` | 3 162 | **PETG** o nylon | Igual que anterior |
| `Pylon_TF` | 122 980 | **PETG al 100 % de relleno** (o sustituir por tubo de Al Ø27×2) | Vertical; en servicio real el pylon es de titanio — la pieza impresa es maqueta |
| `Adaptador_Tarso` | 59 245 | PETG o ABS | Chaflán 2 + fillet 4 |
| `Tornillos_Pie` | 383 | PETG o **tornillería real M6** | Cabeza hex, 4 uds |
| `Arandelas_Pie` | 293 | PETG o arandelas metálicas M6 | 4 uds |
| `Pie_SACH` | 824 400 | **PLA o PETG**, relleno 30-40 % | Planta en cama; SACH por loft de 6 secciones |

### Parámetros de impresión sugeridos

- Capa 0.2 mm; perímetros 4 en piezas estructurales (rodilla, adaptadores, pylon).
- Relleno: 60-100 % en rodilla/adaptadores/pylon; 30-40 % en pie y socket.
- **Holguras ya están en la geometría**: taladro de ojo r5.3 sobre perno r5
  (0.3 mm radiales en PLA) — no escalar las piezas en el slicer.
- Tamaños máximos: pie 280×68 (cama de 220 → **diagonal ≥311 mm** o partir),
  socket 246 de alto, pylon 250 de alto.

### Orden de montaje

1. Pegar `Rodilla_Muslo` sobre `Adaptador_TF` (contacto en z406) y el socket
   encima (contacto en z430): cyanoacrilato o epoxi.
2. Subensamble tibial: `Rodilla_Tibia` + pylon + `Adaptador_Tarso` + pie
   (tornillos/arandelas en el tarso).
3. Deslizar `Barra_Ant` y `Barra_Pst` sobre los pernos femorales desde los
   lados; luego encajar los pernos tibiales en los ojos libres.
4. Retención: los pernos no llevan tope — gota de pegamento en la punta o
   capuchón impreso (no incluido).

### Cinemática (demo de flexión)

Rodilla policéntrica de 4 barras: pernos femorales (±30, 406), tibiales
(14, 374) y (−38, 374); barras L=35.8 / 33.0. La flexión se resuelve por
cinemática inversa (intersección de círculos con trazo continuo de rama);
la tibia rota sobre (0, 0, 374) y las barras sobre sus pernos femorales.
Fotos: `flex4b_{00,15,30,45}.png`.

---

## 2. Prótesis deportiva transtibial (J-blade)

- **Archivo**: `protesis_deportiva.FCStd` — 8 objetos, 520 550 mm³;
  aprobada en 5 rondas iterativas.
- **Materiales** (pieza impresa / equivalente clínico):
  - `Socket`: resina térmica anatómica (brim cortado a 18.4°) / PLA+ prototipo.
  - `Blade_Carbon`: PLA/CF o fibra de carbono real (curva J con ease de remate).
  - `Pylon_Titanio`: titanio real; impreso = PETG 100 % sólo como maqueta.
  - `Adaptador`, `Anillo_Monta`: aluminio anodizado / acero (o PLA plata).
  - `Tornillos`, `Arandelas`, `Bulones`: tornillería estándar o PETG.
- Previews: `montaje_lado.png`, `montaje_34.png`, `protesis_iso.png`.
- STL: aún no exportados (pedir con `Mesh.export` si se necesitan).

---

## Verificación continua

- `test_extended_tools.py`: **27/27 PASS** (tools de ejemplos incluidas).
- `validate_freecad_mcp.py`: catálogo **30 tools, PASS**.
- Regenerar STLs desde FreeCAD si cambia la geometría
  (`Mesh.export` por objeto hacia `examples/stl/`).
