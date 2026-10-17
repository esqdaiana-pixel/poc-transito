import { useEffect, useState } from 'react'
import DeckGL from '@deck.gl/react'
import { BitmapLayer, ScatterplotLayer } from '@deck.gl/layers'
import { TileLayer } from '@deck.gl/geo-layers'
import { supabase } from './supabaseClient'

const COLORES = {
  Alto: [220, 38, 38],
  Medio: [245, 158, 11],
  Bajo: [34, 139, 230],
}
const VISTA_INICIAL = { longitude: -58.44, latitude: -34.6, zoom: 11, pitch: 0 }

const fmt = (n) => n.toLocaleString('es-AR')
// La descripción tiene la forma "AU 25 de Mayo - km 7.9"
const autopistaDe = (p) => p.descripcion.split(' - km ')[0]
const kmDe = (p) => p.descripcion.split(' - km ')[1]

function App() {
  const [puntos, setPuntos] = useState([])
  const [seleccionado, setSeleccionado] = useState(null)

  useEffect(() => {
    async function cargar() {
      const { data, error } = await supabase
        .from('puntos')
        .select('nombre, categoria, latitud, longitud, valor, descripcion')
      console.log('data:', data, 'error:', error)
      if (!error) setPuntos(data)
    }
    cargar()
  }, [])

  // Indicadores generales, calculados con los datos de Supabase
  const total = puntos.length
  const promedio = total
    ? Math.round(puntos.reduce((suma, p) => suma + p.valor, 0) / total)
    : 0
  const altos = puntos.filter((p) => p.categoria === 'Alto').length
  const maximo = total
    ? puntos.reduce((m, p) => (p.valor > m.valor ? p : m), puntos[0])
    : null

  // Estadísticas de UN sensor, comparado con el resto
  function estadisticas(p) {
    const orden = [...puntos].sort((a, b) => b.valor - a.valor)
    const ranking = orden.findIndex((x) => x.nombre === p.nombre) + 1

    const mismaAutopista = puntos
      .filter((x) => autopistaDe(x) === autopistaDe(p))
      .sort((a, b) => b.valor - a.valor)
    const rankingAutopista = mismaAutopista.findIndex((x) => x.nombre === p.nombre) + 1
    const promedioAutopista = Math.round(
      mismaAutopista.reduce((s, x) => s + x.valor, 0) / mismaAutopista.length
    )

    return {
      ranking,
      rankingAutopista,
      cantAutopista: mismaAutopista.length,
      promedioAutopista,
      difPromedio: promedio ? Math.round((p.valor / promedio - 1) * 100) : 0,
      pctMaximo: maximo ? Math.round((p.valor / maximo.valor) * 100) : 0,
    }
  }

  const detalle = seleccionado ? estadisticas(seleccionado) : null

  // Capa 1: fondo de calles (mosaicos de OpenStreetMap)
  const fondo = new TileLayer({
    id: 'fondo',
    data: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    minZoom: 0,
    maxZoom: 19,
    tileSize: 256,
    renderSubLayers: (props) => {
      const [[oeste, sur], [este, norte]] = props.tile.boundingBox
      return new BitmapLayer(props, {
        data: null,
        image: props.data,
        bounds: [oeste, sur, este, norte],
      })
    },
  })

  // Capa 2: sensores. El seleccionado se resalta con un borde oscuro grueso
  const capa = new ScatterplotLayer({
    id: 'sensores',
    data: puntos,
    pickable: true,
    getPosition: (d) => [d.longitud, d.latitud],
    getRadius: (d) => 50 + d.valor / 20,
    radiusMinPixels: 5,
    getFillColor: (d) => [...COLORES[d.categoria], 190],
    stroked: true,
    lineWidthUnits: 'pixels',
    getLineWidth: (d) => (d.nombre === seleccionado?.nombre ? 4 : 1),
    getLineColor: (d) =>
      d.nombre === seleccionado?.nombre ? [17, 24, 39] : [255, 255, 255],
    updateTriggers: {
      getLineWidth: [seleccionado?.nombre],
      getLineColor: [seleccionado?.nombre],
    },
  })

  return (
    <div className="app">
      <header>
        <h1>Tránsito en autopistas de la Ciudad de Buenos Aires</h1>
        <p>
          Promedio de vehículos por hora · sentido A · lunes a viernes de 6 a 10 hs · enero 2026
          · Hacé clic en un sensor para ver su detalle
        </p>
        <div className="kpis">
          <div className="kpi"><strong>{total}</strong><span>Sensores registrados</span></div>
          <div className="kpi"><strong>{fmt(promedio)}</strong><span>Vehículos por hora (promedio)</span></div>
          <div className="kpi"><strong>{altos}</strong><span>Sensores con tránsito alto</span></div>
          <div className="kpi">
            <strong>{maximo ? fmt(maximo.valor) : '-'}</strong>
            <span>Máximo{maximo ? ` (${maximo.nombre})` : ''}</span>
          </div>
        </div>
      </header>

      <div className="mapa">
        <DeckGL
          initialViewState={VISTA_INICIAL}
          controller={true}
          layers={[fondo, capa]}
          onClick={(info) => setSeleccionado(info.object || null)}
          getTooltip={({ object }) => {
            if (!object) return null
            const e = estadisticas(object)
            return {
              html: `<b>${object.nombre}</b><br/>${object.descripcion}<br/>
                     <b>${fmt(object.valor)}</b> veh/h · puesto ${e.ranking} de ${total}`,
              style: { fontSize: '13px' },
            }
          }}
        />

        {seleccionado && detalle && (
          <div className="panel">
            <button className="cerrar" onClick={() => setSeleccionado(null)}>×</button>
            <h2>{seleccionado.nombre}</h2>
            <p className="tramo">{autopistaDe(seleccionado)} · km {kmDe(seleccionado)}</p>
            <span className={`badge ${seleccionado.categoria}`}>
              Tránsito {seleccionado.categoria.toLowerCase()}
            </span>

            <div className="grande">
              <strong>{fmt(seleccionado.valor)}</strong>
              <span>vehículos por hora (promedio de 6 a 10 hs)</span>
            </div>
            <div className="barra"><div style={{ width: `${detalle.pctMaximo}%` }} /></div>
            <p className="nota-barra">{detalle.pctMaximo}% del sensor con más tránsito</p>

            <div className="fila"><span>Puesto general</span><b>{detalle.ranking} de {total}</b></div>
            <div className="fila">
              <span>Frente al promedio ({fmt(promedio)})</span>
              <b>{detalle.difPromedio > 0 ? '+' : ''}{detalle.difPromedio}%</b>
            </div>
            <div className="fila">
              <span>Puesto en su autopista</span>
              <b>{detalle.rankingAutopista} de {detalle.cantAutopista}</b>
            </div>
            <div className="fila">
              <span>Promedio de su autopista</span>
              <b>{fmt(detalle.promedioAutopista)}</b>
            </div>
            <div className="fila">
              <span>Coordenadas</span>
              <b>{seleccionado.latitud.toFixed(5)}, {seleccionado.longitud.toFixed(5)}</b>
            </div>
          </div>
        )}

        <div className="leyenda">
          <div><span className="punto" style={{ background: 'rgb(220,38,38)' }} />Alto</div>
          <div><span className="punto" style={{ background: 'rgb(245,158,11)' }} />Medio</div>
          <div><span className="punto" style={{ background: 'rgb(34,139,230)' }} />Bajo</div>
        </div>
        <div style={{ position: 'absolute', bottom: 4, right: 8, zIndex: 1, fontSize: 11,
                      background: 'rgba(255,255,255,0.7)', padding: '2px 6px' }}>
          © OpenStreetMap
        </div>
      </div>
    </div>
  )
}

export default App