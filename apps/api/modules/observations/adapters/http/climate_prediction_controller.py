from rest_framework.response import Response
from rest_framework.views import APIView

from modules.observations.adapters.http.climate_prediction_serializer import ClimatePredictionSerializer
from modules.observations.composition import observation_service


class ClimatePredictionController(APIView):
    """``/api/climate-predictions/latest/`` : dernière prédiction par zone active."""

    def get(self, request):
        predictions = observation_service().latest_climate_predictions()
        return Response(ClimatePredictionSerializer(predictions, many=True).data)
