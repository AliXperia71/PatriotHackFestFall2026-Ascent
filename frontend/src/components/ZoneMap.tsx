import { CircleMarker, MapContainer, TileLayer, Tooltip } from 'react-leaflet'
import type { Zone } from '../api'

interface Props {
  zones: Zone[]
  selected: string | null
  onSelect: (zoneId: string) => void
  colorFor: (z: Zone) => string
  labelFor: (z: Zone) => string
}

export default function ZoneMap({ zones, selected, onSelect, colorFor, labelFor }: Props) {
  return (
    <MapContainer center={[38.82, -77.29]} zoom={10} className="map">
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {zones.map((z) => (
        <CircleMarker
          key={z.zone_id}
          center={[z.lat, z.lon]}
          radius={selected === z.zone_id ? 20 : 15}
          pathOptions={{
            color: selected === z.zone_id ? '#111' : colorFor(z),
            fillColor: colorFor(z),
            fillOpacity: 0.75,
            weight: 3,
          }}
          eventHandlers={{ click: () => onSelect(z.zone_id) }}
        >
          <Tooltip permanent direction="top" offset={[0, -14]}>
            {z.zone_id}: {labelFor(z)}
          </Tooltip>
        </CircleMarker>
      ))}
    </MapContainer>
  )
}
