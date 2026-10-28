import { createBrowserRouter, RouterProvider } from "react-router";
import { routes } from "./routes";
import { AuthProvider } from "./stores/authStore";
import { DashboardProvider } from "./stores/dashboardStore";

const router = createBrowserRouter(routes);

/** Racine : états partagés (authentification, tableau de bord) puis routeur. */
export default function App() {
  return (
    <AuthProvider>
      <DashboardProvider>
        <RouterProvider router={router} />
      </DashboardProvider>
    </AuthProvider>
  );
}
