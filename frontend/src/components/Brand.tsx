import { useI18n } from '../i18n/core'
import { Link } from 'react-router-dom'
import { Icon } from './Icon'

export function Brand() {
  const { t } = useI18n()
  return (
    <Link className="brand" to="/" aria-label={t("SwasthyaLens home")}>
      <span className="brand__mark"><Icon name="heart" /></span>
      <span>Swasthya<span className="brand__lens">Lens</span></span>
    </Link>
  )
}
