import { useEffect, useState } from "react";
import { getOrders, createOrder, updateOrder, deleteOrder } from "../api/ordersApi";
import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";
import EmptyState from "../components/EmptyState";

function OrdersPage({ auth, mode }) {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [form, setForm] = useState({ product_id: "", supplier_id: "", quantity: "", unit_price: "", status: "PENDING" });

  const isAdmin = auth?.role === "ADMIN";
  const isAdminOrManager = auth?.role === "ADMIN" || auth?.role === "SUPPLY_CHAIN_MANAGER";
  const isSupplier = auth?.role === "SUPPLIER" || mode === "supplier";

  const loadOrders = async () => {
    try {
      setLoading(true);
      setError("");
      const data = await getOrders();
      setOrders(data || []);
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to load orders.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOrders();
  }, []);

  const handleCreate = async (event) => {
    event.preventDefault();
    try {
      setError("");
      setSuccessMsg("");
      await createOrder({
        ...form,
        quantity: Number(form.quantity),
        unit_price: Number(form.unit_price),
      });
      setForm({ product_id: "", supplier_id: "", quantity: "", unit_price: "", status: "PENDING" });
      setSuccessMsg("Order created successfully.");
      await loadOrders();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to create order.");
    }
  };

  const handleStatusUpdate = async (orderId, currentStatus) => {
    try {
      setError("");
      setSuccessMsg("");
      const nextStatus = currentStatus === "PENDING" ? "IN_TRANSIT" : currentStatus === "IN_TRANSIT" ? "DELIVERED" : "PENDING";
      await updateOrder(orderId, { status: nextStatus });
      setSuccessMsg(`Order #${orderId} status updated to ${nextStatus}.`);
      await loadOrders();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to update order.");
    }
  };

  const handleDelete = async (orderId) => {
    try {
      setError("");
      setSuccessMsg("");
      await deleteOrder(orderId);
      setSuccessMsg(`Order #${orderId} deleted.`);
      await loadOrders();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to delete order.");
    }
  };

  if (loading) return <Loading message="Loading orders..." />;

  return (
    <div className="page-container">
      <section className="page-heading">
        <div>
          <p className="page-eyebrow">ORDER OPERATIONS</p>
          <h1>{isSupplier ? "My Orders" : "Orders"}</h1>
        </div>
      </section>

      {error && <ErrorMessage title="Orders error" message={error} onRetry={loadOrders} />}

      {successMsg && (
        <div className="success-banner">
          <span style={{ fontSize: "16px" }}>✓</span>
          <strong>{successMsg}</strong>
        </div>
      )}

      {isAdminOrManager && (
        <section className="investigation-card" style={{ marginBottom: "24px" }}>
          <div className="section-header">
            <div>
              <span className="section-eyebrow">CREATE</span>
              <h2>Create order</h2>
            </div>
          </div>

          <form onSubmit={handleCreate} className="form-grid">
            <input className="search-input" value={form.product_id} onChange={(e) => setForm({ ...form, product_id: e.target.value })} placeholder="Product ID" required />
            <input className="search-input" value={form.supplier_id} onChange={(e) => setForm({ ...form, supplier_id: e.target.value })} placeholder="Supplier ID" required />
            <input className="search-input" type="number" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} placeholder="Quantity" required />
            <input className="search-input" type="number" step="0.01" value={form.unit_price} onChange={(e) => setForm({ ...form, unit_price: e.target.value })} placeholder="Unit Price" required />
            <select className="search-input" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              <option value="PENDING">PENDING</option>
              <option value="IN_TRANSIT">IN_TRANSIT</option>
              <option value="DELIVERED">DELIVERED</option>
            </select>
            <button type="submit" className="primary-button" style={{ height: "42px" }}>Create Order</button>
          </form>
        </section>
      )}

      <section className="data-table-wrapper">
        {orders.length === 0 ? (
          <EmptyState title="No orders" message={isSupplier ? "No orders found for your supplier account." : "There are currently no orders."} />
        ) : (
          <table className="risk-table">
            <thead>
              <tr>
                <th>Order ID</th>
                <th>Product</th>
                <th>Supplier</th>
                <th>Qty</th>
                <th>Unit Price</th>
                <th>Order Date</th>
                <th>Status</th>
                {isAdminOrManager && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.order_id}>
                  <td>#{order.order_id}</td>
                  <td>{order.product_id}</td>
                  <td>{order.supplier_id}</td>
                  <td>{order.quantity}</td>
                  <td>${Number(order.unit_price || 0).toFixed(2)}</td>
                  <td>{order.order_date ? order.order_date.split("T")[0] : "-"}</td>
                  <td>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        fontSize: "12px",
                        fontWeight: "600",
                        backgroundColor:
                          order.status === "DELIVERED"
                            ? "rgba(212, 175, 55, 0.12)"
                            : order.status === "IN_TRANSIT"
                            ? "rgba(212, 175, 55, 0.10)"
                            : "#1C1C1C",
                        color:
                          order.status === "DELIVERED"
                            ? "#D4AF37"
                            : order.status === "IN_TRANSIT"
                            ? "#E5C45A"
                            : "#B8B8B8",
                      }}
                    >
                      {order.status}
                    </span>
                  </td>
                  {isAdminOrManager && (
                    <td>
                      <button
                        className="secondary-button"
                        style={{ marginRight: "8px" }}
                        onClick={() => handleStatusUpdate(order.order_id, order.status)}
                      >
                        Status
                      </button>
                      {isAdmin && (
                        <button className="secondary-button" onClick={() => handleDelete(order.order_id)}>
                          Cancel
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

export default OrdersPage;
