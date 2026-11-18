import { CircleMarker, MapContainer, TileLayer, Tooltip } from 'react-leaflet'
import { STATUS_COLOR, STATUS_LABEL, type Zone } from '../api'

interface Props {
  zones: Zone[]
  selected: string | null
  onSelect: (zoneId: string) => void
}

export default function ZoneMap({ zones, selected, onSelect }: Props) {
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
            color: selected === z.zone_id ? '#111' : STATUS_COLOR[z.status],
            fillColor: STATUS_COLOR[z.status],
            fillOpacity: 0.75,
            weight: 3,
          }}
          eventHandlers={{ click: () => onSelect(z.zone_id) }}
        >
          <Tooltip>
            {z.name} ({z.zone_id}): {STATUS_LABEL[z.status]}
          </Tooltip>
        </CircleMarker>
      ))}
    </MapContainer>
  )
}
