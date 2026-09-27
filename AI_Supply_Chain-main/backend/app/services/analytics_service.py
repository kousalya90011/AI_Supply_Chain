from app.services.data_service import DataService

from app.analytics.supplier_risk import SupplierRiskAnalyzer
from app.analytics.delivery_risk import DeliveryRiskAnalyzer
from app.analytics.inventory_risk import InventoryRiskAnalyzer
from app.analytics.route_risk import RouteRiskAnalyzer
from app.analytics.product_sales import ProductSalesAnalyzer
from app.analytics.dashboard_metrics import DashboardMetrics


class AnalyticsService:

    def __init__(self):
        self.data_service = DataService()

        self.supplier_analyzer = SupplierRiskAnalyzer()
        self.delivery_analyzer = DeliveryRiskAnalyzer()
        self.inventory_analyzer = InventoryRiskAnalyzer(
            self.data_service
        )
        self.route_analyzer = RouteRiskAnalyzer()
        self.sales_analyzer = ProductSalesAnalyzer()

        self.dashboard = DashboardMetrics()

    def get_data(self):
        return self.data_service.load_data()

    def supplier_risk(self):
        datasets = self.get_data()["datasets"]

        orders = datasets["orders_extended"]

        return self.supplier_analyzer.analyze(orders)

    def delivery_risk(self):
        datasets = self.get_data()["datasets"]

        orders = datasets["orders_extended"]

        return self.delivery_analyzer.analyze(orders)

    def inventory_risk(self, top_n: int | None = None):
        return self.inventory_analyzer.analyze(
            top_n=top_n
        )

    def route_risk(self):
        datasets = self.get_data()["datasets"]

        orders = datasets["orders_extended"]

        return self.route_analyzer.analyze(orders)

    def product_sales(self, top_n: int | None = None):
        datasets = self.get_data()["datasets"]

        orders = datasets["orders_extended"]

        return self.sales_analyzer.analyze(
            orders,
            top_n=top_n
        )

    def dashboard_metrics(self):
        datasets = self.get_data()["datasets"]

        return self.dashboard.calculate(
            datasets["orders_extended"],
            datasets["inventory"]
        )
    