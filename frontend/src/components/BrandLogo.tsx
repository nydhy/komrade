import { useState } from 'react'

interface BrandLogoProps {
  variant?: 'header' | 'auth'
  className?: string
}

export function BrandLogo({ variant = 'header', className = '' }: BrandLogoProps) {
  const [failed, setFailed] = useState(false)
  const sizeClass = variant === 'auth' ? 'brand-logo-img-auth' : 'brand-logo-img-header'

  return (
    <div className={`brand-logo ${className}`.trim()}>
      {!failed ? (
        <img
          src="/komrade_logo.png"
          alt="komrade"
          className={sizeClass}
          onError={() => setFailed(true)}
        />
      ) : (
        <span className="heading-md text-gradient">komrade</span>
      )}
    </div>
  )
}
