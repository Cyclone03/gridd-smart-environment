from rest_framework.routers import SimpleRouter

from .controllers.alarm_rule_controller import AlarmRuleController
from .controllers.alert_controller import AlertController

router = SimpleRouter()
router.register("alarm-rules", AlarmRuleController, basename="alarm-rule")
router.register("alerts", AlertController, basename="alert")

urlpatterns = router.urls
