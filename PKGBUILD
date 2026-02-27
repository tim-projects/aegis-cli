# Maintainer: Tim Jefferies <tim.jefferies@gmail.com>
pkgname=aegis-tui
pkgver=0.1.0
pkgrel=1
pkgdesc="An unofficial interactive command-line interface for viewing Aegis Authenticator TOTP codes."
arch=('any')
url="https://github.com/tim-projects/${pkgname}"
license=('GPL3')
depends=('python' 'python-pyotp' 'python-cryptography')
makedepends=('python')
source=("${pkgname}::git+${url}.git#branch=main")
sha256sums=('SKIP')

build() {
  true
}

package() {
  cd "${srcdir}"

  install -d "${pkgdir}/usr/lib/python3.13/site-packages/aegis_tui"
  install -m 644 aegis_tui/* "${pkgdir}/usr/lib/python3.13/site-packages/aegis_tui/"

  install -d "${pkgdir}/usr/bin"
  
  cat > "${pkgdir}/usr/bin/aegis-tui" << 'EOF'
#!/bin/bash
exec python3 -m aegis_tui.aegis_main "$@"
EOF
  chmod 755 "${pkgdir}/usr/bin/aegis-tui"

  cat > "${pkgdir}/usr/bin/aegis-cli" << 'EOF'
#!/bin/bash
exec python3 -m aegis_tui.aegis_cli "$@"
EOF
  chmod 755 "${pkgdir}/usr/bin/aegis-cli"

  install -d "${pkgdir}/usr/share/licenses/${pkgname}"
  install -m 644 LICENSE "${pkgdir}/usr/share/licenses/${pkgname}/"
}
