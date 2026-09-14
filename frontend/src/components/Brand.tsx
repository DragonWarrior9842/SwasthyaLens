import { Link } from 'react-router-dom'
import { Icon } from './Icon'

export function Brand() {
  return (
    <Link className="brand" to="/" aria-label="SwasthyaLens home">
      <span className="brand__mark"><Icon name="heart" /></span>
      <span>Swasthya<span className="brand__lens">Lens</span></span>
    </Link>
  )
}
