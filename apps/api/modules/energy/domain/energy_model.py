from .power_breakdown import PowerBreakdown


class EnergyModel:
    """Modèle stationnaire de la puissance électrique d'un espace (logique pure).

    - éclairage : surface × densité, réduit à 10 % sans occupant ;
    - équipements : puissance fixe + puissance par occupant ;
    - chauffage / climatisation : bilan thermique
          besoin = (UA + 1,2 × débit d'air neuf) × (T_int − T_ext) − apports internes
      où les apports internes sont les occupants (75 W chacun), l'éclairage et
      les équipements. Un besoin positif est couvert par le chauffage
      (÷ COP chauffage), un besoin négatif par la climatisation (÷ COP froid).

    Il s'agit d'une **estimation** : aucune consommation n'est mesurée.
    """

    PERSON_SENSIBLE_GAIN_W = 75.0
    # ρ·cp de l'air ≈ 1,2 kJ/(m³·K) → 1,2 W par (L/s) et par degré.
    AIR_HEAT_W_PER_L_S_K = 1.2
    UNOCCUPIED_LIGHTING_FRACTION = 0.1

    def power(self, profile, indoor_temperature, occupancy) -> PowerBreakdown:
        occupancy = max(occupancy, 0)
        lighting = profile.floor_area_m2 * profile.lighting_w_per_m2
        if occupancy <= 0:
            lighting *= self.UNOCCUPIED_LIGHTING_FRACTION
        equipment = profile.equipment_base_w + profile.equipment_w_per_person * occupancy

        if indoor_temperature is None:
            return PowerBreakdown(lighting, equipment, 0.0, 0.0, hvac_estimated=False)

        delta = indoor_temperature - profile.outdoor_temperature_c
        ventilation = self.AIR_HEAT_W_PER_L_S_K * profile.ventilation_l_s_per_person * occupancy
        losses = (profile.envelope_ua_w_per_k + ventilation) * delta
        gains = self.PERSON_SENSIBLE_GAIN_W * occupancy + lighting + equipment
        need = losses - gains
        heating = need / profile.heating_cop if need > 0 else 0.0
        cooling = -need / profile.cooling_cop if need < 0 else 0.0
        return PowerBreakdown(lighting, equipment, heating, cooling, hvac_estimated=True)
