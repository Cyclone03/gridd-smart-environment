import { Compass } from "lucide-react";
import { Link } from "react-router";
import { PageHeader } from "../components/common/PageHeader";

export function NotFoundView() {
  return (
    <main className="dashboard page-view narrow">
      <PageHeader
        icon={Compass}
        overline="Erreur 404"
        title="Page introuvable"
        description="Cette adresse ne correspond à aucun écran."
      />
      <Link className="primary-button" to="/">
        Retour à la vue d’ensemble
      </Link>
    </main>
  );
}
