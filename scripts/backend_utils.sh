#!/bin/bash

# 🔧 Backend MQTT - Scripts de Utilidad
# ====================================

# Configuración
BACKEND_URL="http://localhost:5000"
DASHBOARD_URL="http://localhost:5001"
DB_NAME="tu_base_de_datos"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para mostrar ayuda
show_help() {
    echo "🔧 Backend MQTT - Scripts de Utilidad"
    echo "======================================"
    echo ""
    echo "Uso: $0 [OPCION]"
    echo ""
    echo "Opciones:"
    echo "  health          - Verificar estado del sistema"
    echo "  test-hardware   - Probar verificación de hardware"
    echo "  test-empresa    - Probar verificación de empresa"
    echo "  test-sede       - Probar verificación de sede"
    echo "  test-complete   - Ejecutar prueba completa"
    echo "  add-hardware    - Agregar nuevo hardware"
    echo "  add-empresa     - Agregar nueva empresa"
    echo "  add-sede        - Agregar nueva sede"
    echo "  list-hardware   - Listar todo el hardware"
    echo "  list-empresas   - Listar todas las empresas"
    echo "  list-sedes      - Listar todas las sedes"
    echo "  monitor         - Monitoreo continuo"
    echo "  stats           - Mostrar estadísticas"
    echo "  logs            - Ver logs del sistema"
    echo "  diagnose        - Diagnóstico completo"
    echo "  setup           - Configuración inicial"
    echo "  help            - Mostrar esta ayuda"
    echo ""
}

# Función para mostrar status con colores
show_status() {
    local status=$1
    local message=$2
    
    case $status in
        "OK")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "ERROR")
            echo -e "${RED}❌ $message${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠️  $message${NC}"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ️  $message${NC}"
            ;;
    esac
}

# Verificar estado del sistema
check_health() {
    echo "🏥 Verificando estado del sistema..."
    
    # Verificar backend
    if curl -s -f "$BACKEND_URL/health" > /dev/null 2>&1; then
        health=$(curl -s "$BACKEND_URL/health" | jq -r '.status')
        if [ "$health" = "healthy" ]; then
            show_status "OK" "Backend disponible"
        else
            show_status "WARNING" "Backend degradado"
        fi
    else
        show_status "ERROR" "Backend no disponible"
        return 1
    fi
    
    # Verificar dashboard
    if curl -s -f "$DASHBOARD_URL/api/health" > /dev/null 2>&1; then
        show_status "OK" "Dashboard disponible"
    else
        show_status "WARNING" "Dashboard no disponible"
    fi
    
    # Verificar MongoDB
    if mongo --quiet --eval "db.runCommand('ping')" "$DB_NAME" > /dev/null 2>&1; then
        show_status "OK" "MongoDB conectado"
    else
        show_status "ERROR" "MongoDB no disponible"
        return 1
    fi
    
    # Verificar Mosquitto
    if systemctl is-active --quiet mosquitto; then
        show_status "OK" "Mosquitto activo"
    else
        show_status "WARNING" "Mosquitto no activo"
    fi
    
    return 0
}

# Probar verificación de hardware
test_hardware() {
    local hardware_name=${1:-"Semaforo001"}
    
    echo "🔍 Probando verificación de hardware: $hardware_name"
    
    response=$(curl -s -X POST "$BACKEND_URL/verificar-hardware" \
        -H "Content-Type: application/json" \
        -d "{\"nombre\": \"$hardware_name\"}")
    
    if [ $? -eq 0 ]; then
        exists=$(echo "$response" | jq -r '.existe')
        if [ "$exists" = "true" ]; then
            show_status "OK" "Hardware encontrado"
            echo "$response" | jq '.hardware'
        else
            show_status "ERROR" "Hardware no encontrado"
            echo "$response" | jq '.mensaje'
        fi
    else
        show_status "ERROR" "Error en la petición"
    fi
}

# Probar verificación de empresa
test_empresa() {
    local empresa_name=${1:-"empresa1"}
    
    echo "🏢 Probando verificación de empresa: $empresa_name"
    
    response=$(curl -s -X POST "$BACKEND_URL/verificar-empresa" \
        -H "Content-Type: application/json" \
        -d "{\"nombre\": \"$empresa_name\"}")
    
    if [ $? -eq 0 ]; then
        exists=$(echo "$response" | jq -r '.existe')
        if [ "$exists" = "true" ]; then
            show_status "OK" "Empresa encontrada"
            echo "$response" | jq '.empresa'
        else
            show_status "ERROR" "Empresa no encontrada"
            echo "$response" | jq '.mensaje'
        fi
    else
        show_status "ERROR" "Error en la petición"
    fi
}

# Probar verificación de sede
test_sede() {
    local empresa=${1:-"empresa1"}
    local sede=${2:-"principal"}
    
    echo "🏢 Probando verificación de sede: $empresa - $sede"
    
    response=$(curl -s -X POST "$BACKEND_URL/verificar-sede" \
        -H "Content-Type: application/json" \
        -d "{\"empresa\": \"$empresa\", \"sede\": \"$sede\"}")
    
    if [ $? -eq 0 ]; then
        exists=$(echo "$response" | jq -r '.existe')
        if [ "$exists" = "true" ]; then
            show_status "OK" "Sede encontrada"
            echo "$response" | jq '.sede'
        else
            show_status "ERROR" "Sede no encontrada"
            echo "$response" | jq '.mensaje'
        fi
    else
        show_status "ERROR" "Error en la petición"
    fi
}

# Ejecutar prueba completa
test_complete() {
    local empresa=${1:-"empresa1"}
    local tipo=${2:-"semaforo"}
    local sede=${3:-"principal"}
    local nombre=${4:-"Semaforo001"}
    
    echo "🧪 Ejecutando prueba completa..."
    echo "   Empresa: $empresa"
    echo "   Tipo: $tipo"
    echo "   Sede: $sede"
    echo "   Hardware: $nombre"
    
    response=$(curl -s -X POST "$BACKEND_URL/prueba-completa" \
        -H "Content-Type: application/json" \
        -d "{
            \"empresa\": \"$empresa\",
            \"tipo_alerta\": \"$tipo\",
            \"sede\": \"$sede\",
            \"nombre\": \"$nombre\"
        }")
    
    if [ $? -eq 0 ]; then
        success=$(echo "$response" | jq -r '.resultado.alerta_creada')
        if [ "$success" = "true" ]; then
            show_status "OK" "Prueba completa exitosa"
            echo "$response" | jq -r '.mensaje'
            echo "ID de alerta: $(echo "$response" | jq -r '.resultado.alerta_id')"
            echo "Usuarios notificados: $(echo "$response" | jq -r '.resultado.usuarios_notificados')"
        else
            show_status "ERROR" "Prueba completa fallida"
            echo "$response" | jq '.'
        fi
    else
        show_status "ERROR" "Error en la petición"
    fi
}

# Agregar hardware interactivo
add_hardware() {
    echo "➕ Agregar nuevo hardware"
    echo "========================"
    
    read -p "Nombre del hardware: " nombre
    read -p "Tipo (semaforo/alarma/sensor): " tipo
    read -p "Empresa: " empresa
    read -p "Sede: " sede
    read -p "Ubicación: " ubicacion
    read -p "Latitud: " lat
    read -p "Longitud: " lng
    
    # Validar datos requeridos
    if [[ -z "$nombre" || -z "$tipo" || -z "$empresa" || -z "$sede" ]]; then
        show_status "ERROR" "Faltan datos requeridos"
        return 1
    fi
    
    # Crear documento JSON
    local json_doc=$(cat <<EOF
{
  "nombre": "$nombre",
  "tipo": "$tipo",
  "estado": "activo",
  "empresa": "$empresa",
  "sede": "$sede",
  "ubicacion": "$ubicacion",
  "coordenadas": {
    "lat": $lat,
    "lng": $lng
  },
  "fecha_instalacion": new Date(),
  "ultima_actualizacion": new Date()
}
EOF
)
    
    # Insertar en MongoDB
    echo "db.hardware.insertOne($json_doc)" | mongo "$DB_NAME"
    
    if [ $? -eq 0 ]; then
        show_status "OK" "Hardware agregado exitosamente"
        
        # Verificar que se agregó correctamente
        test_hardware "$nombre"
    else
        show_status "ERROR" "Error agregando hardware"
    fi
}

# Agregar empresa interactiva
add_empresa() {
    echo "➕ Agregar nueva empresa"
    echo "======================="
    
    read -p "Nombre de la empresa: " nombre
    read -p "Email de contacto: " email
    read -p "Teléfono de contacto: " telefono
    read -p "Nombre del usuario admin: " admin_name
    read -p "Email del usuario admin: " admin_email
    read -p "Teléfono del usuario admin: " admin_phone
    
    # Validar datos requeridos
    if [[ -z "$nombre" || -z "$email" || -z "$admin_name" || -z "$admin_email" ]]; then
        show_status "ERROR" "Faltan datos requeridos"
        return 1
    fi
    
    # Crear documento JSON
    local json_doc=$(cat <<EOF
{
  "nombre": "$nombre",
  "estado": "activo",
  "fecha_creacion": new Date(),
  "contacto": {
    "telefono": "$telefono",
    "email": "$email"
  },
  "usuarios": [
    {
      "nombre": "$admin_name",
      "email": "$admin_email",
      "rol": "admin",
      "telefono": "$admin_phone",
      "activo": true
    }
  ],
  "configuracion": {
    "notificaciones_email": true,
    "notificaciones_sms": true,
    "alertas_criticas": true
  }
}
EOF
)
    
    # Insertar en MongoDB
    echo "db.empresas.insertOne($json_doc)" | mongo "$DB_NAME"
    
    if [ $? -eq 0 ]; then
        show_status "OK" "Empresa agregada exitosamente"
        
        # Verificar que se agregó correctamente
        test_empresa "$nombre"
    else
        show_status "ERROR" "Error agregando empresa"
    fi
}

# Agregar sede interactiva
add_sede() {
    echo "➕ Agregar nueva sede"
    echo "===================="
    
    read -p "Nombre de la sede: " nombre
    read -p "Empresa: " empresa
    read -p "Ubicación (ciudad): " ubicacion
    read -p "Dirección: " direccion
    read -p "Latitud: " lat
    read -p "Longitud: " lng
    
    # Validar datos requeridos
    if [[ -z "$nombre" || -z "$empresa" || -z "$ubicacion" ]]; then
        show_status "ERROR" "Faltan datos requeridos"
        return 1
    fi
    
    # Crear documento JSON
    local json_doc=$(cat <<EOF
{
  "nombre": "$nombre",
  "empresa": "$empresa",
  "ubicacion": "$ubicacion",
  "direccion": "$direccion",
  "estado": "activo",
  "coordenadas": {
    "lat": $lat,
    "lng": $lng
  },
  "horarios": {
    "apertura": "06:00",
    "cierre": "22:00",
    "dias_operacion": ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado"]
  }
}
EOF
)
    
    # Insertar en MongoDB
    echo "db.sedes.insertOne($json_doc)" | mongo "$DB_NAME"
    
    if [ $? -eq 0 ]; then
        show_status "OK" "Sede agregada exitosamente"
        
        # Verificar que se agregó correctamente
        test_sede "$empresa" "$nombre"
    else
        show_status "ERROR" "Error agregando sede"
    fi
}

# Listar hardware
list_hardware() {
    echo "📋 Listando hardware..."
    
    mongo --quiet "$DB_NAME" --eval "
        db.hardware.find({}, {
            nombre: 1,
            tipo: 1,
            estado: 1,
            empresa: 1,
            sede: 1,
            ubicacion: 1,
            _id: 0
        }).forEach(function(doc) {
            print(doc.nombre + ' | ' + doc.tipo + ' | ' + doc.estado + ' | ' + doc.empresa + ' | ' + doc.sede + ' | ' + doc.ubicacion);
        });
    "
}

# Listar empresas
list_empresas() {
    echo "📋 Listando empresas..."
    
    mongo --quiet "$DB_NAME" --eval "
        db.empresas.find({}, {
            nombre: 1,
            estado: 1,
            'contacto.email': 1,
            usuarios: 1,
            _id: 0
        }).forEach(function(doc) {
            var usuarios_count = doc.usuarios ? doc.usuarios.length : 0;
            print(doc.nombre + ' | ' + doc.estado + ' | ' + doc.contacto.email + ' | ' + usuarios_count + ' usuarios');
        });
    "
}

# Listar sedes
list_sedes() {
    echo "📋 Listando sedes..."
    
    mongo --quiet "$DB_NAME" --eval "
        db.sedes.find({}, {
            nombre: 1,
            empresa: 1,
            ubicacion: 1,
            estado: 1,
            _id: 0
        }).forEach(function(doc) {
            print(doc.nombre + ' | ' + doc.empresa + ' | ' + doc.ubicacion + ' | ' + doc.estado);
        });
    "
}

# Monitoreo continuo
monitor_system() {
    echo "📊 Iniciando monitoreo continuo (Ctrl+C para detener)..."
    
    while true; do
        clear
        echo "=== MONITOREO MQTT SYSTEM $(date) ==="
        echo ""
        
        # Estado del sistema
        if curl -s -f "$BACKEND_URL/health" > /dev/null 2>&1; then
            health=$(curl -s "$BACKEND_URL/health" | jq -r '.status')
            show_status "OK" "Backend: $health"
        else
            show_status "ERROR" "Backend no disponible"
        fi
        
        # Métricas del dashboard
        if curl -s -f "$DASHBOARD_URL/api/metrics" > /dev/null 2>&1; then
            metrics=$(curl -s "$DASHBOARD_URL/api/metrics")
            total_alerts=$(echo "$metrics" | jq -r '.total_alerts')
            alerts_per_min=$(echo "$metrics" | jq -r '.alerts_per_minute')
            uptime=$(echo "$metrics" | jq -r '.uptime_formatted')
            
            echo ""
            echo "📊 Métricas:"
            echo "   Total alertas: $total_alerts"
            echo "   Alertas/minuto: $alerts_per_min"
            echo "   Uptime: $uptime"
            
            # Tiempo de respuesta
            response_stats=$(echo "$metrics" | jq -r '.response_time_stats')
            if [ "$response_stats" != "null" ]; then
                avg_time=$(echo "$response_stats" | jq -r '.avg')
                echo "   Tiempo respuesta: ${avg_time}s"
            fi
        else
            show_status "WARNING" "Dashboard no disponible"
        fi
        
        # Contadores de base de datos
        echo ""
        echo "📋 Base de datos:"
        hardware_count=$(mongo --quiet "$DB_NAME" --eval "db.hardware.count()")
        empresas_count=$(mongo --quiet "$DB_NAME" --eval "db.empresas.count()")
        sedes_count=$(mongo --quiet "$DB_NAME" --eval "db.sedes.count()")
        alerts_count=$(mongo --quiet "$DB_NAME" --eval "db.mqtt_alerts.count()")
        
        echo "   Hardware: $hardware_count"
        echo "   Empresas: $empresas_count"
        echo "   Sedes: $sedes_count"
        echo "   Alertas: $alerts_count"
        
        # Esperar 30 segundos
        sleep 30
    done
}

# Mostrar estadísticas
show_stats() {
    echo "📊 Estadísticas del Sistema"
    echo "========================="
    
    # Métricas generales
    if curl -s -f "$DASHBOARD_URL/api/metrics" > /dev/null 2>&1; then
        metrics=$(curl -s "$DASHBOARD_URL/api/metrics")
        echo "Uptime: $(echo "$metrics" | jq -r '.uptime_formatted')"
        echo "Total alertas: $(echo "$metrics" | jq -r '.total_alerts')"
        echo "Alertas/minuto: $(echo "$metrics" | jq -r '.alerts_per_minute')"
        
        response_stats=$(echo "$metrics" | jq -r '.response_time_stats')
        if [ "$response_stats" != "null" ]; then
            echo "Tiempo respuesta promedio: $(echo "$response_stats" | jq -r '.avg')s"
        fi
    fi
    
    echo ""
    echo "📋 Estadísticas de Base de Datos"
    echo "==============================="
    
    # Hardware por tipo
    echo "Hardware por tipo:"
    mongo --quiet "$DB_NAME" --eval "
        db.hardware.aggregate([
            { \$group: { _id: '\$tipo', count: { \$sum: 1 } } },
            { \$sort: { count: -1 } }
        ]).forEach(function(doc) {
            print('  ' + doc._id + ': ' + doc.count);
        });
    "
    
    # Hardware por estado
    echo "Hardware por estado:"
    mongo --quiet "$DB_NAME" --eval "
        db.hardware.aggregate([
            { \$group: { _id: '\$estado', count: { \$sum: 1 } } },
            { \$sort: { count: -1 } }
        ]).forEach(function(doc) {
            print('  ' + doc._id + ': ' + doc.count);
        });
    "
    
    # Alertas de los últimos 7 días
    echo ""
    echo "Alertas de los últimos 7 días:"
    alerts_7d=$(mongo --quiet "$DB_NAME" --eval "
        db.mqtt_alerts.find({
            timestamp: { \$gte: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000) }
        }).count()
    ")
    echo "  $alerts_7d alertas"
}

# Ver logs
show_logs() {
    local log_type=${1:-"system"}
    
    echo "📋 Mostrando logs: $log_type"
    echo "========================="
    
    case $log_type in
        "system")
            if [ -f "logs/mqtt/system.log" ]; then
                tail -n 50 logs/mqtt/system.log
            else
                show_status "WARNING" "No hay logs de sistema"
            fi
            ;;
        "alerts")
            if [ -f "logs/alerts/alerts.log" ]; then
                tail -n 50 logs/alerts/alerts.log
            else
                show_status "WARNING" "No hay logs de alertas"
            fi
            ;;
        "errors")
            if [ -f "logs/errors/errors.log" ]; then
                tail -n 50 logs/errors/errors.log
            else
                show_status "OK" "No hay logs de errores"
            fi
            ;;
        *)
            show_status "ERROR" "Tipo de log inválido: $log_type"
            echo "Tipos disponibles: system, alerts, errors"
            ;;
    esac
}

# Diagnóstico completo
diagnose_system() {
    echo "🔍 Diagnóstico completo del sistema"
    echo "================================="
    
    # 1. Verificar servicios del sistema
    echo "1. Verificando servicios..."
    systemctl is-active --quiet mongod && show_status "OK" "MongoDB activo" || show_status "ERROR" "MongoDB inactivo"
    systemctl is-active --quiet mosquitto && show_status "OK" "Mosquitto activo" || show_status "WARNING" "Mosquitto inactivo"
    
    # 2. Verificar puertos
    echo ""
    echo "2. Verificando puertos..."
    netstat -tlnp | grep -q ":5000" && show_status "OK" "Puerto 5000 (Backend) abierto" || show_status "ERROR" "Puerto 5000 cerrado"
    netstat -tlnp | grep -q ":5001" && show_status "OK" "Puerto 5001 (Dashboard) abierto" || show_status "WARNING" "Puerto 5001 cerrado"
    netstat -tlnp | grep -q ":1883" && show_status "OK" "Puerto 1883 (MQTT) abierto" || show_status "WARNING" "Puerto 1883 cerrado"
    netstat -tlnp | grep -q ":27017" && show_status "OK" "Puerto 27017 (MongoDB) abierto" || show_status "ERROR" "Puerto 27017 cerrado"
    
    # 3. Verificar conectividad
    echo ""
    echo "3. Verificando conectividad..."
    check_health
    
    # 4. Verificar base de datos
    echo ""
    echo "4. Verificando base de datos..."
    hardware_count=$(mongo --quiet "$DB_NAME" --eval "db.hardware.count()" 2>/dev/null)
    empresas_count=$(mongo --quiet "$DB_NAME" --eval "db.empresas.count()" 2>/dev/null)
    sedes_count=$(mongo --quiet "$DB_NAME" --eval "db.sedes.count()" 2>/dev/null)
    
    if [ "$hardware_count" -gt 0 ]; then
        show_status "OK" "Hardware: $hardware_count registros"
    else
        show_status "WARNING" "No hay hardware configurado"
    fi
    
    if [ "$empresas_count" -gt 0 ]; then
        show_status "OK" "Empresas: $empresas_count registros"
    else
        show_status "WARNING" "No hay empresas configuradas"
    fi
    
    if [ "$sedes_count" -gt 0 ]; then
        show_status "OK" "Sedes: $sedes_count registros"
    else
        show_status "WARNING" "No hay sedes configuradas"
    fi
    
    # 5. Verificar logs recientes
    echo ""
    echo "5. Verificando logs recientes..."
    if [ -f "logs/errors/errors.log" ]; then
        error_count=$(tail -n 100 logs/errors/errors.log | wc -l)
        if [ "$error_count" -gt 0 ]; then
            show_status "WARNING" "Errores recientes encontrados ($error_count)"
        else
            show_status "OK" "No hay errores recientes"
        fi
    else
        show_status "OK" "No hay logs de errores"
    fi
    
    echo ""
    echo "================================="
    show_status "OK" "Diagnóstico completado"
}

# Configuración inicial
setup_system() {
    echo "🚀 Configuración inicial del sistema"
    echo "===================================="
    
    # Verificar dependencias
    echo "1. Verificando dependencias..."
    
    # Verificar MongoDB
    if command -v mongo &> /dev/null; then
        show_status "OK" "MongoDB CLI disponible"
    else
        show_status "ERROR" "MongoDB CLI no encontrado"
        echo "   Instalar con: sudo apt-get install mongodb-clients"
        return 1
    fi
    
    # Verificar jq
    if command -v jq &> /dev/null; then
        show_status "OK" "jq disponible"
    else
        show_status "ERROR" "jq no encontrado"
        echo "   Instalar con: sudo apt-get install jq"
        return 1
    fi
    
    # Verificar curl
    if command -v curl &> /dev/null; then
        show_status "OK" "curl disponible"
    else
        show_status "ERROR" "curl no encontrado"
        echo "   Instalar con: sudo apt-get install curl"
        return 1
    fi
    
    # Verificar que el sistema esté corriendo
    echo ""
    echo "2. Verificando servicios..."
    if ! check_health; then
        show_status "ERROR" "Sistema no disponible. Ejecutar: python start_system.py"
        return 1
    fi
    
    # Datos de ejemplo
    echo ""
    echo "3. Configurando datos de ejemplo..."
    
    # Verificar si ya existen datos
    hardware_count=$(mongo --quiet "$DB_NAME" --eval "db.hardware.count()" 2>/dev/null)
    
    if [ "$hardware_count" -eq 0 ]; then
        echo "   Agregando datos de ejemplo..."
        
        # Script de datos de ejemplo
        cat > /tmp/setup_data.js << 'EOF'
// Agregar empresas
db.empresas.insertMany([
  {
    "nombre": "empresa1",
    "estado": "activo",
    "fecha_creacion": new Date(),
    "contacto": {
      "telefono": "+57 300 123 4567",
      "email": "admin@empresa1.com"
    },
    "usuarios": [
      {
        "nombre": "Juan Pérez",
        "email": "juan@empresa1.com",
        "rol": "admin",
        "telefono": "+57 300 111 2222",
        "activo": true
      },
      {
        "nombre": "María García",
        "email": "maria@empresa1.com",
        "rol": "operador",
        "telefono": "+57 300 333 4444",
        "activo": true
      }
    ],
    "configuracion": {
      "notificaciones_email": true,
      "notificaciones_sms": true,
      "alertas_criticas": true
    }
  }
]);

// Agregar sedes
db.sedes.insertMany([
  {
    "nombre": "principal",
    "empresa": "empresa1",
    "ubicacion": "Bogotá",
    "direccion": "Calle 123 #45-67",
    "estado": "activo",
    "coordenadas": {
      "lat": 4.6097,
      "lng": -74.0817
    },
    "horarios": {
      "apertura": "06:00",
      "cierre": "22:00",
      "dias_operacion": ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado"]
    }
  },
  {
    "nombre": "secundaria",
    "empresa": "empresa1",
    "ubicacion": "Medellín",
    "direccion": "Carrera 50 #30-20",
    "estado": "activo",
    "coordenadas": {
      "lat": 6.2442,
      "lng": -75.5812
    },
    "horarios": {
      "apertura": "07:00",
      "cierre": "21:00",
      "dias_operacion": ["lunes", "martes", "miércoles", "jueves", "viernes"]
    }
  }
]);

// Agregar hardware
db.hardware.insertMany([
  {
    "nombre": "Semaforo001",
    "tipo": "semaforo",
    "estado": "activo",
    "empresa": "empresa1",
    "sede": "principal",
    "ubicacion": "Cruce principal",
    "coordenadas": {
      "lat": 4.6097,
      "lng": -74.0817
    },
    "fecha_instalacion": new Date(),
    "ultima_actualizacion": new Date()
  },
  {
    "nombre": "Alarma001",
    "tipo": "alarma",
    "estado": "activo",
    "empresa": "empresa1",
    "sede": "principal",
    "ubicacion": "Edificio principal",
    "coordenadas": {
      "lat": 4.6095,
      "lng": -74.0815
    },
    "fecha_instalacion": new Date(),
    "ultima_actualizacion": new Date()
  },
  {
    "nombre": "Semaforo002",
    "tipo": "semaforo",
    "estado": "activo",
    "empresa": "empresa1",
    "sede": "secundaria",
    "ubicacion": "Cruce norte",
    "coordenadas": {
      "lat": 6.2442,
      "lng": -75.5812
    },
    "fecha_instalacion": new Date(),
    "ultima_actualizacion": new Date()
  }
]);

print("Datos de ejemplo agregados exitosamente");
EOF
        
        # Ejecutar script
        mongo "$DB_NAME" < /tmp/setup_data.js
        rm /tmp/setup_data.js
        
        show_status "OK" "Datos de ejemplo agregados"
    else
        show_status "INFO" "Ya existen datos en la base de datos"
    fi
    
    # Ejecutar pruebas
    echo ""
    echo "4. Ejecutando pruebas..."
    test_hardware "Semaforo001"
    test_empresa "empresa1"
    test_sede "empresa1" "principal"
    test_complete "empresa1" "semaforo" "principal" "Semaforo001"
    
    echo ""
    echo "================================="
    show_status "OK" "Configuración inicial completada"
    echo ""
    echo "🎯 Accesos rápidos:"
    echo "   Backend: $BACKEND_URL"
    echo "   Dashboard: $DASHBOARD_URL"
    echo "   Monitoreo: $0 monitor"
    echo "   Estadísticas: $0 stats"
}

# Función principal
main() {
    case "${1:-help}" in
        "health")
            check_health
            ;;
        "test-hardware")
            test_hardware "$2"
            ;;
        "test-empresa")
            test_empresa "$2"
            ;;
        "test-sede")
            test_sede "$2" "$3"
            ;;
        "test-complete")
            test_complete "$2" "$3" "$4" "$5"
            ;;
        "add-hardware")
            add_hardware
            ;;
        "add-empresa")
            add_empresa
            ;;
        "add-sede")
            add_sede
            ;;
        "list-hardware")
            list_hardware
            ;;
        "list-empresas")
            list_empresas
            ;;
        "list-sedes")
            list_sedes
            ;;
        "monitor")
            monitor_system
            ;;
        "stats")
            show_stats
            ;;
        "logs")
            show_logs "$2"
            ;;
        "diagnose")
            diagnose_system
            ;;
        "setup")
            setup_system
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# Ejecutar función principal
main "$@"
