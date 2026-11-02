# infra-vps-tecnomovil

Todo lo que necesitas para subir tu proyecto al VPS del equipo: la guía paso a paso, las reglas que debe cumplir tu proyecto, las plantillas y el flujo de GitHub Actions que despliega solo cada vez que haces merge a `main`.

La guía también la puede seguir un asistente de IA (LLM) que te ayude: empieza por [guia/00-empieza-aqui.md](guia/00-empieza-aqui.md).

Este repositorio es **público**. Nunca guardes aquí IP, contraseñas, claves, tokens, archivos `.env` ni certificados.

## La guía

1. [guia/00-empieza-aqui.md](guia/00-empieza-aqui.md): cómo funciona el VPS, sus reglas y qué instalar en tu equipo.
2. [guia/02-preparar-proyecto.md](guia/02-preparar-proyecto.md): cómo dejar tu proyecto listo.
3. [guia/03-subir-proyecto.md](guia/03-subir-proyecto.md): dominio, alta en el VPS, GitHub Actions y primer despliegue.

## Cómo llega tu proyecto a los usuarios

```
Usuarios ─HTTPS─> Cloudflare (tu dominio) ─> VPS: nginx ─┬─> tu web estática
                                                          └─> tu contenedor (API)
                                                               └─> PostgreSQL compartido (tu base)
```

- Haces un PR: se ejecutan tus pruebas y las del VPS.
- Haces merge a `main`: se construye la imagen y se despliega sin cortes. Si la versión nueva falla, la anterior sigue funcionando.

## Contenido

| Ruta | Qué es | Estado |
|---|---|---|
| `guia/` | La guía | Escrita |
| `herramientas/vps-check` | Comprueba que tu `compose.yml` cumple las reglas del VPS; lo puedes ejecutar en tu equipo | Pendiente |
| `templates/` | Plantillas de nginx para tu web y tu API | Pendiente |
| `ejemplo/` | Proyecto mínimo que sigue la estructura obligatoria | Pendiente |
| `.github/workflows/deploy.yml` | Flujo de despliegue que llama tu proyecto | Pendiente |
| `projects.yml` | Registro de proyectos: dueño, dominios y puertos | Pendiente |

Lo marcado como pendiente se publica antes de que subas tu proyecto.
