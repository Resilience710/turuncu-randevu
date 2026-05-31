// Oturum yardımcıları + sayfa-bazlı role guard.
// API global'ini gerektirir (api.js önce yüklenmeli).

function requireRole(allowedRoles, redirectTo = '/index.html') {
  const session = window.API.getSession();
  if (!session?.user) {
    const next = encodeURIComponent(location.pathname + location.search);
    location.href = `${redirectTo}?next=${next}`;
    return null;
  }
  if (allowedRoles && !allowedRoles.includes(session.user.role)) {
    location.href = roleHome(session.user.role);
    return null;
  }
  return session;
}

function roleHome(role) {
  if (role === 'customer') return '/customer/businesses.html';
  if (role === 'owner' || role === 'staff') return '/owner/dashboard.html';
  return '/index.html';
}

function logout() {
  window.API.clearSession();
  location.href = '/index.html';
}

window.Auth = { requireRole, roleHome, logout };
