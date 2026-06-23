/**
 * =============================================================================
 * TOOL — PROCESAMIENTO DE ESTADÍSTICAS MULTI-VERSIÓN (COLECCIÓN 4)
 * =============================================================================
 * @descripción
 * Script para automatizar la extracción de estadísticas de área para múltiples
 * versiones de la clasificación. 
 * Lógica de activos: 
 * - Versión 1: Proviene de la ruta de clasificación base.
 * - Versiones > 1: Provienen de la ruta de filtros.
 * =============================================================================
 */

// ============================================================================
// 1. CONFIGURACIÓN
// ============================================================================
var country        = 'COLOMBIA';
var regionId       = 30424;
var folder         = 'EXPORT-STATS-COLOMBIA-C4';

// Parámetros de Procesamiento
var versionFiltros = [1, 2,3,4,5,6,7,8,12];               // Versiones a procesar (ej. [1, 4])
var years_process  = ee.List.sequence(1985, 2026); // Rango de años para el cálculo (CSV)
var export_csv     = true;
var export_toAsset = true;

// Parámetros de Visualización
var visualize_on_map = true;                // Activar carga de capas en el mapa
var years_vis        = [2000, 2020];        // Años específicos para visualización rápida

// ============================================================================
// 2. IMPORTACIÓN DE MÓDULOS Y ACTIVOS
// ============================================================================
var paths_directory = require('users/kahuertas/mapbiomas-colombia:mapbiomas-colombia/collection-4/modules/CollectionDirectories.js').paths;
var palette         = require('users/kahuertas/mapbiomas-colombia:mapbiomas-colombia/collection-4/modules/Palettes.js').get('colombiaCol4');

// Definición de Región de Interés (ROI)
var regionsPath   = paths_directory.regionVectorBuffer;
var regionFeature = ee.FeatureCollection(regionsPath).filter(ee.Filter.eq('id_regionC', regionId));
var regionGeo     = regionFeature.geometry();

// Rutas de Colecciones (Clasificación Original y Filtros)
var classPath   = paths_directory.classification;
var filtersPath = paths_directory.classificationFiltros;

// Configuración inicial del mapa
Map.centerObject(regionGeo, 10);
Map.addLayer(regionFeature.style({color: 'red', fillColor: '00000000'}), {}, 'ROI - Region ' + regionId);

// ============================================================================
// 3. LÓGICA DE CÁLCULO (SERVER-SIDE)
// ============================================================================

/**
 * Calcula el área por clase para cada año de la serie.
 * @param {ee.Image} image - Imagen de la versión a procesar.
 * @param {Number} versionVal - Número de la versión.
 * @param {String} versionDesc - Descripción de la versión.
 * @returns {ee.FeatureCollection} Colección con estadísticas anuales.
 */
var calculateStats = function(image, versionVal, versionDesc) {
  
  // Iteración sobre la lista de años en el servidor
  var feats = years_process.map(function(y) {
    var year = ee.Number(y).format('%d');
    var bandName = ee.String('classification_').cat(year);
    
    // Verificación de existencia de banda para evitar errores en años fuera de rango
    return ee.Algorithms.If(
      image.bandNames().contains(bandName),
      (function(){
        // Pre-procesamiento: Forzar entero (Int16) y enmascarar fondo (0)
        var imgYear = image.select(bandName).int16().selfMask(); 
        
        // Creación de imagen de 2 bandas: [Área (ha), Clase]
        var areaImg = ee.Image.pixelArea().divide(1e4).addBands(imgYear);
        
        // Reducción agrupada: Suma de área agrupada por valor de clase
        var groups = areaImg.reduceRegion({
          reducer: ee.Reducer.sum().group({
            groupField: 1,
            groupName: 'class',
          }),
          geometry: regionGeo,
          scale: 30,
          maxPixels: 1e13
        }).get('groups');
        
        // Formateo de resultados en estructura de diccionario plano (IDxx)
        var groupsList = ee.List(groups);
        var baseDict = ee.Dictionary(['year', year, 'version', versionVal, 'descripcion', versionDesc]);
        
        var classDict = groupsList.iterate(function(item, memo){
            item = ee.Dictionary(item);
            var classId = ee.Number(item.get('class')).toInt(); 
            var area = item.get('sum');
            
            // Generación dinámica de nombre de columna (ej. ID03, ID15)
            var classStr = ee.String(classId);
            var colName = ee.Algorithms.If(classId.lt(10), 
                          ee.String('ID0').cat(classStr), 
                          ee.String('ID').cat(classStr));
                          
            return ee.Dictionary(memo).set(colName, area);
        }, baseDict);
        
        // return ee.Feature(null, classDict);
        return ee.Feature(ee.Geometry.Point([0, 0]), classDict);
        
      })(),
      null // Retorna null si la banda no existe (será filtrado autom.)
    );
  }, true);

  return ee.FeatureCollection(feats);
};

// ============================================================================
// 4. EJECUCIÓN PRINCIPAL Y EXPORTACIÓN
// ============================================================================

versionFiltros.forEach(function(v) {
  
  print('------------------------------------------------');
  print('Iniciando proceso para Versión: ' + v);
  
  // 4.1. Definición de recurso
  var activePath = (v === 1) ? classPath : filtersPath;
  var assetId = activePath + '/' + country + '-' + regionId + '-' + v;
  var image = ee.Image(assetId);
  var descServer = image.get('descripcion'); 
  
  // 4.2. Cálculo de estadísticas crudas
  var fcStatsRaw = calculateStats(image, v, descServer);

  // 4.3. Normalización de Columnas (Relleno de ceros)
  // Paso A: Obtener lista única de todas las clases detectadas en toda la serie temporal
  var allKeys = fcStatsRaw.map(function(f) { 
      return f.set('keys_list', f.propertyNames()); 
  }).aggregate_array('keys_list').flatten().distinct()
    .removeAll(['year', 'version', 'descripcion', 'system:index']);
  
  // Paso B: Crear diccionario base con valor 0 para todas las clases posibles
  var zeroList = ee.List.repeat(0, allKeys.length());
  var zeroDict = ee.Dictionary.fromLists(allKeys, zeroList);

  // Paso C: Fusionar datos reales sobre el diccionario base
  var fcStats = fcStatsRaw.map(function(f) {
      // combine(..., true) asegura que el dato real prevalezca sobre el 0
      var fullDict = zeroDict.combine(f.toDictionary(), true); 
      return ee.Feature(ee.Geometry.Point([0, 0]), fullDict);
  });
  var nameDescript = descServer.getInfo()
                      .replace(/ /g, '-')
                      .replace(/\+/g, '')
                        
  // 4.4. Definición de nombres de salida
  var fileName = "STATS_R" + regionId + "_V" + v; 
  var assetDesc = "R" + regionId + "_V" + v + '-' + nameDescript;
  
  // 4.5. Configuración de Tareas de Exportación
  if(export_csv){
    Export.table.toDrive({
      collection: fcStats,
      description: fileName,
      fileFormat: 'CSV',
      folder: folder,
      selectors: null // null permite detección automática de columnas normalizadas
    });
  }
  
  if(export_toAsset){
    Export.table.toAsset({
      collection: fcStats,
      description: assetDesc,
      assetId: 'projects/mapbiomas-colombia/assets/LULC/COLECCION4/ESTADISTICAS/' + assetDesc,
    });
  }

  // 4.6. Visualización en Mapa (Opcional)
  if (visualize_on_map) {
    var visParam = { min: 0, max: palette.length - 1, palette: palette };

    years_vis.forEach(function(yearVis) {
       var bandName = 'classification_' + yearVis;
       // Carga "perezosa" con verificación visual de errores
       var layer = image.select(bandName).selfMask(); 
       var layerName = 'V' + v + ' | ' + yearVis;
       Map.addLayer(layer, visParam, layerName, false);
    });
  }
});
