"""Normalizador de alertas para TV (schema tv.v1)."""

# ❌ La TV NO interpreta lógica
# ❌ La TV NO discrimina tipos
# ✅ Todo llega normalizado
# ✅ Todo versionado
# ✅ El backend absorbe complejidad
# ✅ Cualquier fuente futura debe mapear a este schema

from typing import Any, Dict, List, Optional


class AlertNormalizationError(ValueError):
    """Error de normalizacion cuando faltan campos obligatorios."""


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _ensure_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    return []


def _normalize_string_list(values: Any) -> List[str]:
    return [_stringify(item) for item in _ensure_list(values)]


def normalize_alert_to_tv(alert: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza una alerta del dominio al schema tv.v1."""
    activacion_alerta = alert.get("activacion_alerta")
    if not isinstance(activacion_alerta, dict) or not activacion_alerta.get("tipo_activacion"):
        raise AlertNormalizationError("Falta alert.activacion_alerta.tipo_activacion")

    base: Dict[str, Any] = {
        "schema_version": "tv.v1",
        "id": "",
        "estado": "",
        "nivel_alerta": "",
        "prioridad": "",
        "nombre": "",
        "descripcion": "",
        "imagen": "",
        "ubicacion": {},
        "instrucciones": [],
        "elementos_necesarios": [],
        "origen": {},
        "contactos": [],
        "dispositivos_notificados": [],
        "timestamps": {},
    }

    base["id"] = _stringify(alert.get("_id") or alert.get("id"))
    base["estado"] = "ACTIVA" if alert.get("activo") else "DESACTIVADA"
    base["prioridad"] = _stringify(alert.get("prioridad"))
    base["nombre"] = _stringify(alert.get("nombre_alerta") or alert.get("nombre"))
    base["descripcion"] = _stringify(alert.get("descripcion"))
    base["imagen"] = _stringify(alert.get("image_alert"))
    base["instrucciones"] = _normalize_string_list(alert.get("instrucciones"))
    base["elementos_necesarios"] = _normalize_string_list(alert.get("elementos_necesarios"))

    data_payload: Dict[str, Any] = {}
    if isinstance(alert.get("data"), dict):
        data_payload = alert.get("data", {})

    nivel_alerta = data_payload.get("tipo_alarma")
    if nivel_alerta is None:
        nivel_alerta = alert.get("tipo_alerta")
    base["nivel_alerta"] = _stringify(nivel_alerta).upper() if nivel_alerta is not None else ""

    ubicacion = alert.get("ubicacion")
    if isinstance(ubicacion, dict):
        base["ubicacion"] = {
            "nombre": _stringify(ubicacion.get("nombre")),
            "direccion": _stringify(ubicacion.get("direccion")),
            "maps": _stringify(
                ubicacion.get("maps")
                or ubicacion.get("url_maps")
                or ubicacion.get("url_open_maps")
            ),
            "open_maps": _stringify(ubicacion.get("url_open_maps")),
        }
    elif isinstance(ubicacion, str):
        base["ubicacion"] = {
            "nombre": _stringify(ubicacion),
            "direccion": "",
            "maps": "",
            "open_maps": "",
        }
    else:
        base["ubicacion"] = {
            "nombre": "",
            "direccion": "",
            "maps": "",
            "open_maps": "",
        }

    base["origen"] = {
        "tipo": _stringify(activacion_alerta.get("tipo_activacion")),
        "nombre": _stringify(activacion_alerta.get("nombre")),
    }

    contactos: List[Dict[str, str]] = []
    for contacto in _ensure_list(alert.get("numeros_telefonicos")):
        if not isinstance(contacto, dict):
            continue
        contactos.append(
            {
                "nombre": _stringify(contacto.get("nombre")),
                "rol": _stringify(contacto.get("rol")),
                "telefono": _stringify(contacto.get("telefono") or contacto.get("numero")),
            }
        )
    base["contactos"] = contactos

    dispositivos = alert.get("topics_notificacion")
    if dispositivos is None:
        dispositivos = alert.get("topics_otros_hardware")
    base["dispositivos_notificados"] = _normalize_string_list(dispositivos)

    base["timestamps"] = {
        "creacion": _stringify(alert.get("fecha_creacion")),
        "actualizacion": _stringify(alert.get("fecha_actualizacion")),
    }

    return base


def build_tv_topic(empresa: str, sede: str, pantalla: str) -> str:
    """Construye el topic MQTT para TV."""
    return f"rescue/tv/{empresa}/{sede}/{pantalla}"
