export function useAuth() {
  // Compatibility shim only. Real auth is not connected in this standalone pass.
  return {
    user: {
      name: "Demo Artist",
      email: "demo@howardvox.ai",
    },
    loading: false,
    isAuthenticated: true,
  };
}
