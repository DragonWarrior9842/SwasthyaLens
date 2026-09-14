import type { ComponentPropsWithRef } from 'react'
import { Link, type LinkProps } from 'react-router-dom'

type ButtonVariant = 'primary' | 'secondary' | 'ghost'
type ButtonSize = 'sm' | 'md'

interface ButtonStyleProps {
  variant?: ButtonVariant
  size?: ButtonSize
}

function buttonClassName(variant: ButtonVariant, size: ButtonSize, className = '') {
  return `button button--${variant} button--${size} ${className}`.trim()
}

export function Button({ variant = 'primary', size = 'md', className, type = 'button', ...props }: ComponentPropsWithRef<'button'> & ButtonStyleProps) {
  return <button type={type} className={buttonClassName(variant, size, className)} {...props} />
}

export function ButtonLink({ variant = 'primary', size = 'md', className, ...props }: LinkProps & ButtonStyleProps) {
  return <Link className={buttonClassName(variant, size, className)} {...props} />
}
