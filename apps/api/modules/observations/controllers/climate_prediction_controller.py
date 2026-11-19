from rest_framework.response import Response
from rest_framework.views import APIView

from modules.observations.serializers.climate_prediction_serializer import ClimatePredictionSerializer
from modules.observations.services.observation_service import ObservationService


class ClimatePredictionController(APIView):
    """``/api/climate-predictions/latest/`` : dernière prédiction par zone active."""

    def get(self, request):
        predictions = ObservationService().latest_climate_predictions()
        return Response(ClimatePredictionSerializer(predictions, many=True).data)
