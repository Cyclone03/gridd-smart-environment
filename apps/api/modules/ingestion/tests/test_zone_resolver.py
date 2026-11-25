from django.test import SimpleTestCase

from modules.ingestion.core.domain.zone_resolver import ZoneResolver


class ZoneResolverTests(SimpleTestCase):
    def test_reads_the_zone_from_the_usual_metadata_formats(self):
        resolver = ZoneResolver()
        for metadata in (
            {"zone": {"id": "meeting-room", "label": "Salle"}},
            {"zone": {"code": "meeting-room"}},
            {"zone": "meeting-room"},
            {"zone_id": "meeting-room"},
            {"zoneId": "meeting-room"},
        ):
            with self.subTest(metadata=metadata):
                self.assertEqual(resolver.resolve(metadata, "node01").code, "meeting-room")

    def test_configured_node_mapping_then_no_zone_from_the_node_id(self):
        resolver = ZoneResolver({"node01": "open-workspace"})
        self.assertEqual(resolver.resolve({}, "node01").code, "open-workspace")
        self.assertIsNone(resolver.resolve({}, "node02"))
        self.assertIsNone(ZoneResolver().resolve({"zone": {"label": "sans code"}}, "node03"))
