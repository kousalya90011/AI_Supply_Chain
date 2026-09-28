import { useEffect, useState } from "react";
import { getOffers, createOffer, updateOffer, acceptOffer, rejectOffer, withdrawOffer, deleteOffer } from "../api/offersApi";
import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";
import EmptyState from "../components/EmptyState";

function OffersPage({ auth, mode }) {
  const [offers, setOffers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionSuccess, setActionSuccess] = useState("");

  const isSupplier = auth?.role === "SUPPLIER" || mode === "supplier";
  const isAdminOrManager = auth?.role === "ADMIN" || auth?.role === "SUPPLY_CHAIN_MANAGER";

  // Filter state for Manager / Admin
  const [filters, setFilters] = useState({
    status: "",
    supplier_id: "",
    product_id: "",
  });

  // Create form state (for Supplier)
  const defaultCreateForm = {
    product_id: "",
    quantity: "",
    unit_price: "",
    delivery_days: 7,
    valid_until: "",
  };
  const [createForm, setCreateForm] = useState(defaultCreateForm);

  // Edit form state (for Supplier editing a PENDING offer)
  const [editingOfferId, setEditingOfferId] = useState(null);
  const [editForm, setEditForm] = useState({
    quantity: "",
    unit_price: "",
    delivery_days: "",
    valid_until: "",
  });

  const loadOffers = async () => {
    try {
      setLoading(true);
      setError("");
      const params = {};
      if (filters.status) params.status = filters.status;
      if (filters.supplier_id) params.supplier_id = filters.supplier_id.trim();
      if (filters.product_id) params.product_id = filters.product_id.trim();

      const data = await getOffers(params);
      setOffers(data || []);
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to load offers.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOffers();
  }, [filters.status]);

  const handleApplyFilter = (e) => {
    e.preventDefault();
    loadOffers();
  };

  const handleClearFilter = () => {
    setFilters({ status: "", supplier_id: "", product_id: "" });
    getOffers().then(data => setOffers(data || [])).catch(() => {});
  };

  const handleCreate = async (event) => {
    event.preventDefault();
    try {
      setError("");
      setActionSuccess("");
      await createOffer({
        product_id: createForm.product_id.trim(),
        quantity: Number(createForm.quantity),
        unit_price: Number(createForm.unit_price),
        delivery_days: Number(createForm.delivery_days),
        valid_until: createForm.valid_until ? `${createForm.valid_until}T23:59:59` : undefined,
      });
      setCreateForm(defaultCreateForm);
      setActionSuccess("Offer created successfully.");
      await loadOffers();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to create offer.");
    }
  };

  const startEdit = (offer) => {
    setEditingOfferId(offer.offer_id);
    setEditForm({
      quantity: offer.quantity,
      unit_price: offer.unit_price,
      delivery_days: offer.delivery_days,
      valid_until: offer.valid_until ? offer.valid_until.split("T")[0] : "",
    });
  };

  const cancelEdit = () => {
    setEditingOfferId(null);
    setEditForm({ quantity: "", unit_price: "", delivery_days: "", valid_until: "" });
  };

  const handleSaveEdit = async (offerId) => {
    try {
      setError("");
      setActionSuccess("");
      await updateOffer(offerId, {
        quantity: Number(editForm.quantity),
        unit_price: Number(editForm.unit_price),
        delivery_days: Number(editForm.delivery_days),
        valid_until: editForm.valid_until ? `${editForm.valid_until}T23:59:59` : undefined,
      });
      setEditingOfferId(null);
      setActionSuccess(`Offer #${offerId} updated successfully.`);
      await loadOffers();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to update offer.");
    }
  };

  const handleDecision = async (offerId, decision) => {
    try {
      setError("");
      setActionSuccess("");
      if (decision === "accept") {
        await acceptOffer(offerId);
        setActionSuccess(`Offer #${offerId} accepted and order created.`);
      } else if (decision === "reject") {
        await rejectOffer(offerId);
        setActionSuccess(`Offer #${offerId} rejected.`);
      } else if (decision === "withdraw") {
        await withdrawOffer(offerId);
        setActionSuccess(`Offer #${offerId} withdrawn.`);
      }
      await loadOffers();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to process offer action.");
    }
  };

  const handleDelete = async (offerId) => {
    try {
      setError("");
      await deleteOffer(offerId);
      setActionSuccess(`Offer #${offerId} deleted.`);
      await loadOffers();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to delete offer.");
    }
  };

  if (loading) return <Loading message="Loading offers..." />;

  return (
    <div className="page-container">
      <section className="page-heading">
        <div>
          <p className="page-eyebrow">{isSupplier ? "SUPPLIER PORTAL" : "OFFERS REVIEW"}</p>
          <h1>{isSupplier ? "My Offers" : "Supplier Offers"}</h1>
        </div>
      </section>

      {error && <ErrorMessage title="Offer Action Error" message={error} onRetry={loadOffers} />}

      {actionSuccess && (
        <div className="success-banner">
          <span style={{ fontSize: "16px" }}>✓</span>
          <strong>{actionSuccess}</strong>
        </div>
      )}

      {/* Supplier Create Offer Form */}
      {isSupplier && (
        <section className="investigation-card" style={{ marginBottom: "24px" }}>
          <div className="section-header">
            <div>
              <span className="section-eyebrow">CREATE OFFER</span>
              <h2>Submit New Offer</h2>
            </div>
          </div>

          <form onSubmit={handleCreate} className="form-grid">
            <div>
              <label>Product ID</label>
              <input
                className="search-input"
                value={createForm.product_id}
                onChange={(e) => setCreateForm({ ...createForm, product_id: e.target.value })}
                placeholder="e.g. P00003"
                required
              />
            </div>
            <div>
              <label>Quantity</label>
              <input
                className="search-input"
                type="number"
                min="1"
                value={createForm.quantity}
                onChange={(e) => setCreateForm({ ...createForm, quantity: e.target.value })}
                placeholder="e.g. 100"
                required
              />
            </div>
            <div>
              <label>Unit Price ($)</label>
              <input
                className="search-input"
                type="number"
                step="0.01"
                min="0"
                value={createForm.unit_price}
                onChange={(e) => setCreateForm({ ...createForm, unit_price: e.target.value })}
                placeholder="e.g. 125.50"
                required
              />
            </div>
            <div>
              <label>Delivery Days</label>
              <input
                className="search-input"
                type="number"
                min="1"
                value={createForm.delivery_days}
                onChange={(e) => setCreateForm({ ...createForm, delivery_days: e.target.value })}
                placeholder="e.g. 7"
                required
              />
            </div>
            <div>
              <label>Valid Until</label>
              <input
                className="search-input"
                type="date"
                value={createForm.valid_until}
                onChange={(e) => setCreateForm({ ...createForm, valid_until: e.target.value })}
                required
              />
            </div>
            <div>
              <button type="submit" className="primary-button" style={{ width: "100%", height: "42px" }}>
                Create Offer
              </button>
            </div>
          </form>
        </section>
      )}

      {/* Supplier Editing Form Card (when editing a pending offer) */}
      {editingOfferId && (
        <section className="investigation-card" style={{ marginBottom: "20px", border: "1px solid rgba(59, 130, 246, 0.4)" }}>
          <div className="section-header">
            <div>
              <span className="section-eyebrow">EDIT PENDING OFFER</span>
              <h2>Modifying Offer #{editingOfferId}</h2>
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px", alignItems: "end" }}>
            <div>
              <label style={{ fontSize: "12px", opacity: 0.8, display: "block", marginBottom: "4px" }}>Quantity</label>
              <input
                className="search-input"
                type="number"
                min="1"
                value={editForm.quantity}
                onChange={(e) => setEditForm({ ...editForm, quantity: e.target.value })}
                required
              />
            </div>
            <div>
              <label style={{ fontSize: "12px", opacity: 0.8, display: "block", marginBottom: "4px" }}>Unit Price ($)</label>
              <input
                className="search-input"
                type="number"
                step="0.01"
                min="0"
                value={editForm.unit_price}
                onChange={(e) => setEditForm({ ...editForm, unit_price: e.target.value })}
                required
              />
            </div>
            <div>
              <label style={{ fontSize: "12px", opacity: 0.8, display: "block", marginBottom: "4px" }}>Delivery Days</label>
              <input
                className="search-input"
                type="number"
                min="1"
                value={editForm.delivery_days}
                onChange={(e) => setEditForm({ ...editForm, delivery_days: e.target.value })}
                required
              />
            </div>
            <div>
              <label style={{ fontSize: "12px", opacity: 0.8, display: "block", marginBottom: "4px" }}>Valid Until</label>
              <input
                className="search-input"
                type="date"
                value={editForm.valid_until}
                onChange={(e) => setEditForm({ ...editForm, valid_until: e.target.value })}
                required
              />
            </div>
            <div style={{ display: "flex", gap: "8px" }}>
              <button className="primary-button" style={{ height: "42px", flex: 1 }} onClick={() => handleSaveEdit(editingOfferId)}>
                Save Changes
              </button>
              <button className="secondary-button" style={{ height: "42px" }} onClick={cancelEdit}>
                Cancel
              </button>
            </div>
          </div>
        </section>
      )}

      {/* Manager / Admin Filter Section */}
      {isAdminOrManager && (
        <section className="investigation-card" style={{ marginBottom: "20px" }}>
          <div className="section-header">
            <div>
              <span className="section-eyebrow">FILTER OFFERS</span>
              <h2>Search & Filter</h2>
            </div>
          </div>

          <form onSubmit={handleApplyFilter} style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px", alignItems: "end" }}>
            <div>
              <label style={{ fontSize: "12px", opacity: 0.8, display: "block", marginBottom: "4px" }}>Status</label>
              <select
                className="search-input"
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              >
                <option value="">All Statuses</option>
                <option value="PENDING">PENDING</option>
                <option value="ACCEPTED">ACCEPTED</option>
                <option value="REJECTED">REJECTED</option>
                <option value="WITHDRAWN">WITHDRAWN</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: "12px", opacity: 0.8, display: "block", marginBottom: "4px" }}>Supplier</label>
              <input
                className="search-input"
                value={filters.supplier_id}
                onChange={(e) => setFilters({ ...filters, supplier_id: e.target.value })}
                placeholder="Filter by Supplier ID"
              />
            </div>

            <div>
              <label style={{ fontSize: "12px", opacity: 0.8, display: "block", marginBottom: "4px" }}>Product</label>
              <input
                className="search-input"
                value={filters.product_id}
                onChange={(e) => setFilters({ ...filters, product_id: e.target.value })}
                placeholder="Filter by Product ID"
              />
            </div>

            <div style={{ display: "flex", gap: "8px" }}>
              <button type="submit" className="primary-button" style={{ height: "42px", flex: 1 }}>
                Apply
              </button>
              <button type="button" className="secondary-button" style={{ height: "42px" }} onClick={handleClearFilter}>
                Clear
              </button>
            </div>
          </form>
        </section>
      )}

      {/* Offers Table */}
      <section className="data-table-wrapper">
        {offers.length === 0 ? (
          <EmptyState title="No offers found" message="No supplier offers match the current criteria." />
        ) : (
          <table className="risk-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Supplier</th>
                <th>Product</th>
                <th>Qty</th>
                <th>Unit Price</th>
                <th>Lead Time</th>
                <th>Valid Until</th>
                <th>Status</th>
                <th>Reviewed By</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {offers.map((offer) => {
                const isPending = offer.status === "PENDING";
                return (
                  <tr key={offer.offer_id}>
                    <td>#{offer.offer_id}</td>
                    <td>{offer.supplier_id}</td>
                    <td>{offer.product_id}</td>
                    <td>{offer.quantity}</td>
                    <td>${Number(offer.unit_price || 0).toFixed(2)}</td>
                    <td>{offer.delivery_days} days</td>
                    <td>{offer.valid_until ? offer.valid_until.split("T")[0] : "-"}</td>
                    <td>
                      <span
                        style={{
                          display: "inline-block",
                          padding: "2px 8px",
                          borderRadius: "4px",
                          fontSize: "12px",
                          fontWeight: "600",
                          backgroundColor:
                            offer.status === "ACCEPTED"
                              ? "rgba(34, 197, 94, 0.15)"
                              : offer.status === "REJECTED"
                              ? "rgba(239, 68, 68, 0.15)"
                              : offer.status === "WITHDRAWN"
                              ? "rgba(107, 114, 128, 0.15)"
                              : "rgba(234, 179, 8, 0.15)",
                          color:
                            offer.status === "ACCEPTED"
                              ? "#22c55e"
                              : offer.status === "REJECTED"
                              ? "#ef4444"
                              : offer.status === "WITHDRAWN"
                              ? "#9ca3af"
                              : "#eab308",
                        }}
                      >
                        {offer.status}
                      </span>
                    </td>
                    <td>
                      {offer.reviewed_by ? (
                        <span>{offer.reviewed_by}</span>
                      ) : (
                        <span style={{ opacity: 0.5 }}>-</span>
                      )}
                    </td>
                    <td>
                      {/* Manager/Admin Actions */}
                      {isAdminOrManager && (
                        <>
                          {isPending ? (
                            <>
                              <button
                                className="secondary-button"
                                style={{ marginRight: "8px", borderColor: "rgba(34, 197, 94, 0.4)", color: "#22c55e" }}
                                onClick={() => handleDecision(offer.offer_id, "accept")}
                              >
                                Accept
                              </button>
                              <button
                                className="secondary-button"
                                style={{ marginRight: "8px", borderColor: "rgba(239, 68, 68, 0.4)", color: "#ef4444" }}
                                onClick={() => handleDecision(offer.offer_id, "reject")}
                              >
                                Reject
                              </button>
                            </>
                          ) : (
                            <span style={{ fontSize: "12px", opacity: 0.6, marginRight: "8px" }}>Reviewed</span>
                          )}
                        </>
                      )}

                      {/* Supplier Actions */}
                      {isSupplier && (
                        <>
                          {isPending ? (
                            <>
                              <button
                                className="secondary-button"
                                style={{ marginRight: "8px" }}
                                onClick={() => startEdit(offer)}
                              >
                                Edit
                              </button>
                              <button
                                className="secondary-button"
                                style={{ borderColor: "rgba(239, 68, 68, 0.4)", color: "#ef4444" }}
                                onClick={() => handleDecision(offer.offer_id, "withdraw")}
                              >
                                Withdraw
                              </button>
                            </>
                          ) : (
                            <span style={{ fontSize: "12px", opacity: 0.6 }}>Locked</span>
                          )}
                        </>
                      )}

                      {/* Admin-only Delete */}
                      {auth?.role === "ADMIN" && (
                        <button
                          className="secondary-button"
                          style={{ marginLeft: "8px", opacity: 0.7 }}
                          onClick={() => handleDelete(offer.offer_id)}
                        >
                          Delete
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

export default OffersPage;
