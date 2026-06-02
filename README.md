# PAC Monitor — GADMR Compras Públicas

Dashboard de monitoreo del Plan Anual de Contratación (PAC) para el GADMR, con vínculo al sistema e-DOC y asistente Claude integrado.

---

## ¿Qué hace este sistema?

- **Carga Excel del PAC** de cada dirección del GADMR (detección automática de columnas)
- **Consolida** todos los procesos en un solo tablero de control
- **Vincula** cada proceso PAC con su trámite en el e-DOC (`egobedoc.gadmriobamba.gob.ec:8081`)
- **Alertas** de procesos sin vínculo e-DOC o en estado problemático
- **Reporte** por dirección con avance de vinculación
- **Asistente Claude** (Haiku) integrado para consultas en lenguaje natural
- **Exportación** a Excel consolidado

Los datos se guardan en `localStorage` del navegador — no se envían a ningún servidor.

---

## Despliegue en GitHub Pages

### 1. Crear el repositorio

```bash
# En GitHub: New repository → pac-gadmr (público)
git clone https://github.com/fborjaf07/pac-gadmr.git
cd pac-gadmr
```

### 2. Subir los archivos

```bash
cp index.html pac-gadmr/
cp pac_schema.json pac-gadmr/
cd pac-gadmr
git add .
git commit -m "feat: PAC Monitor inicial"
git push origin main
```

### 3. Activar GitHub Pages

- Repositorio → Settings → Pages
- Source: `Deploy from a branch` → `main` → `/root`
- Guardar

URL pública: `https://fborjaf07.github.io/pac-gadmr/`

---

## Estructura del proyecto

```
pac-gadmr/
├── index.html          ← Dashboard completo (HTML puro, sin dependencias locales)
├── pac_schema.json     ← Esquema de referencia del PAC
└── README.md
```

---

## Uso

### Cargar el PAC de una dirección

1. Ir a **Cargar PAC** en el menú lateral
2. Seleccionar la dirección
3. Arrastrar el Excel del PAC (`.xlsx`, `.xls` o `.csv`)
4. Verificar el mapeo de columnas y hacer clic en **Importar datos**

El sistema reconoce automáticamente columnas con nombres como:
- `Descripción`, `Objeto`, `Detalle` → descripción del proceso
- `Monto`, `Presupuesto`, `Valor referencial` → monto
- `Tipo`, `Modalidad`, `Procedimiento` → tipo de contratación
- `Responsable`, `Director`, `Gestor` → responsable
- `Fecha`, `Inicio`, `Planificada` → fecha planificada
- `Estado`, `Status` → estado del proceso
- `CPC`, `Clasificador` → código CPC

### Vincular con e-DOC

En la tabla de **Procesos PAC**, columna **Vínculo e-DOC**:
- Clic en `＋` para vincular un trámite nuevo
- Clic en `✎` para editar el vínculo existente
- El número de trámite abre directamente el e-DOC al hacer clic

### Configurar Claude

- Ingresar la API Key en la parte inferior del menú lateral
- La key se guarda en `localStorage` del navegador
- Se usa el modelo `claude-haiku-4-5-20251001`
- **No se guarda en GitHub Actions ni en el repositorio**

---

## Formato del Excel del PAC

Columnas típicas del PAC SERCOP que el sistema mapea automáticamente:

| Columna Excel         | Campo interno        |
|-----------------------|----------------------|
| Código / #PAC         | `num_pac`            |
| Descripción / Objeto  | `descripcion`        |
| Tipo de Contratación  | `tipo`               |
| Presupuesto / Monto   | `monto`              |
| Estado                | `estado`             |
| Fase / Etapa          | `fase`               |
| Responsable           | `responsable`        |
| Fecha planificada     | `fecha_planificada`  |
| Partida presupuest.   | `partida`            |
| CPC / Clasificador    | `cpc`                |

La columna **Trámite e-DOC** se llena manualmente desde el dashboard.

---

## Relación con el sistema de trámites

Este sistema es complementario al monitoreo de trámites existente:

| Sistema | Repositorio | URL |
|---------|-------------|-----|
| Trámites e-DOC | `monitoreo-tramites-gadmr` | `fborjaf07.github.io/monitoreo-tramites-gadmr` |
| PAC Compras | `pac-gadmr` (este) | `fborjaf07.github.io/pac-gadmr` |

El vínculo entre ambos se establece manualmente ingresando el número de trámite e-DOC en cada proceso PAC.

---

## Notas técnicas

- **Sin backend**: todo es HTML+JS estático
- **Sin servidor de autenticación**: la API Key de Claude se guarda solo en localStorage
- **Sin GitHub Actions**: los datos viven en el navegador, no hay scraping
- **Dependencia CDN**: SheetJS desde `cdnjs.cloudflare.com` para leer Excel
- **Compatible**: Chrome, Firefox, Edge, Safari modernos
