// User management functions using localStorage

// Store current user
function setCurrentUser(user) {
  localStorage.setItem('currentUser', JSON.stringify(user));
  // Dispatch event for components that need to know about user changes
  window.dispatchEvent(new CustomEvent('userChanged', { detail: user }));
}

// Get current user
function getCurrentUser() {
  const userStr = localStorage.getItem('currentUser');
  return userStr ? JSON.parse(userStr) : null;
}

// Clear current user
function clearCurrentUser() {
  localStorage.removeItem('currentUser');
  window.dispatchEvent(new CustomEvent('userChanged', { detail: null }));
}

// Check if user is logged in
function isLoggedIn() {
  return getCurrentUser() !== null;
}

// Update user data
function updateUserData(updates) {
  const currentUser = getCurrentUser();
  if (currentUser) {
    const updatedUser = { ...currentUser, ...updates };
    setCurrentUser(updatedUser);
    return updatedUser;
  }
  return null;
}

// Export functions
window.Auth = {
  setCurrentUser,
  getCurrentUser,
  clearCurrentUser,
  isLoggedIn,
  updateUserData
}; 