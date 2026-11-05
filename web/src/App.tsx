import { createBrowserRouter, RouterProvider } from "react-router";
import { routes } from "./routes";
import { DashboardProvider } from "./stores/dashboardStore";

const router = createBrowserRouter(routes);

/** Racine : état partagé du tableau de bord puis routeur. */
export default function App() {
  return (
    <DashboardProvider>
      <RouterProvider router={router} />
    </DashboardProvider>
  );
}
