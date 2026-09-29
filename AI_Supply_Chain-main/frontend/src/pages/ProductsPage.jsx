import { useEffect, useState, useMemo } from "react";
import {
  getProducts,
  getNextProductId,
  createProduct,
  updateProduct,
  approveProduct,
  rejectProduct,
  deleteProduct,
} from "../api/productsApi";
import { createOffer } from "../api/offersApi";
import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";
import EmptyState from "../components/EmptyState";

function getDefaultValidUntil() {
  const d = new Date();
  d.setDate(d.getDate() + 14);
  return d.toISOString().split("T")[0];
}

function ProductsPage({ auth, mode }) {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const [activeTab, setActiveTab] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  // Product creation form
  const [autoProductId, setAutoProductId] = useState("");
  const [form, setForm] = useState({
    name: "",
    category: "",
    unit_cost: "",
    status: "ACTIVE",
    supplier_id: "",
  });
  const [submittingProduct, setSubmittingProduct] = useState(false);

  // Offer creation modal state (for Supplier)
  const [offerProduct, setOfferProduct] = useState(null);
  const [offerForm, setOfferForm] = useState({
    quantity: 100,
    unit_price: "",
    delivery_days: 7,
    valid_until: getDefaultValidUntil(),
  });
  const [offerSubmitting, setOfferSubmitting] = useState(false);
  const [offerError, setOfferError] = useState("");

  // Rejection modal state (for Manager / Admin)
  const [rejectingProduct, setRejectingProduct] = useState(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const [rejectSubmitting, setRejectSubmitting] = useState(false);

  const isAdmin = auth?.role === "ADMIN";
  const isManager = auth?.role === "SUPPLY_CHAIN_MANAGER";
  const isAdminOrManager = isAdmin || isManager;
  const isSupplier = auth?.role === "SUPPLIER" || mode === "supplier";

  const loadProducts = async () => {
    try {
      setLoading(true);
      setError("");
      const data = await getProducts();
      setProducts(data || []);
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to load products.");
    } finally {
      setLoading(false);
    }
  };

  const loadNextId = async () => {
    try {
      const data = await getNextProductId();
      if (data?.next_product_id) {
        setAutoProductId(data.next_product_id);
      }
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    loadProducts();
    loadNextId();
  }, []);

  const handleCreateProduct = async (event) => {
    event.preventDefault();
    try {
      setSubmittingProduct(true);
      setError("");
      setSuccessMsg("");

      const payload = {
        name: form.name.trim(),
        category: form.category.trim(),
        unit_cost: Number(form.unit_cost),
        status: form.status || "ACTIVE",
      };
      if (autoProductId) {
        payload.product_id = autoProductId;
      }
      if (isAdminOrManager && form.supplier_id) {
        payload.supplier_id = form.supplier_id.trim();
      }

      const created = await createProduct(payload);

      setForm({
        name: "",
        category: "",
        unit_cost: "",
        status: "ACTIVE",
        supplier_id: "",
      });

      const assignedId = created?.product_id || autoProductId;
      if (isSupplier) {
        setSuccessMsg(
          `Product ${assignedId} submitted successfully! It is now pending review by a Supply Chain Manager or Administrator.`
        );
      } else {
        setSuccessMsg(`Product ${assignedId} created and approved successfully.`);
      }

      await loadProducts();
      await loadNextId();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to create product.");
    } finally {
      setSubmittingProduct(false);
    }
  };

  const handleApprove = async (productId) => {
    try {
      setError("");
      setSuccessMsg("");
      await approveProduct(productId);
      setSuccessMsg(`Product ${productId} has been approved.`);
      await loadProducts();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to approve product.");
    }
  };

  const handleOpenRejectModal = (product) => {
    setRejectingProduct(product);
    setRejectionReason("");
  };

  const handleConfirmReject = async (e) => {
    e.preventDefault();
    if (!rejectingProduct) return;
    try {
      setRejectSubmitting(true);
      setError("");
      setSuccessMsg("");
      await rejectProduct(rejectingProduct.product_id, rejectionReason.trim());
      setSuccessMsg(`Product ${rejectingProduct.product_id} has been rejected.`);
      setRejectingProduct(null);
      await loadProducts();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to reject product.");
    } finally {
      setRejectSubmitting(false);
    }
  };

  const handleToggleStatus = async (product) => {
    try {
      setError("");
      setSuccessMsg("");
      const newStatus = product.status === "ACTIVE" ? "INACTIVE" : "ACTIVE";
      await updateProduct(product.product_id, { status: newStatus });
      setSuccessMsg(`Product ${product.product_id} marked as ${newStatus}.`);
      await loadProducts();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to update product.");
    }
  };

  const handleDelete = async (productId) => {
    if (!window.confirm(`Are you sure you want to delete product ${productId}?`)) return;
    try {
      setError("");
      setSuccessMsg("");
      await deleteProduct(productId);
      setSuccessMsg(`Product ${productId} deleted.`);
      await loadProducts();
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to delete product.");
    }
  };

  const handleOpenOfferModal = (product) => {
    setOfferProduct(product);
    setOfferForm({
      quantity: 100,
      unit_price: product.unit_cost || 0,
      delivery_days: 7,
      valid_until: getDefaultValidUntil(),
    });
    setOfferError("");
  };

  const handleCreateOfferSubmit = async (e) => {
    e.preventDefault();
    if (!offerProduct) return;
    try {
      setOfferSubmitting(true);
      setOfferError("");
      await createOffer({
        product_id: offerProduct.product_id,
        quantity: Number(offerForm.quantity),
        unit_price: Number(offerForm.unit_price),
        delivery_days: Number(offerForm.delivery_days),
        valid_until: `${offerForm.valid_until}T23:59:59`,
      });
      setSuccessMsg(
        `Offer successfully created for ${offerProduct.name} (${offerProduct.product_id})! You can manage it under My Offers.`
      );
      setOfferProduct(null);
    } catch (err) {
      setOfferError(err?.response?.data?.detail || "Unable to create offer.");
    } finally {
      setOfferSubmitting(false);
    }
  };

  // Filtered products calculation
  const pendingCount = useMemo(
    () => products.filter((p) => p.approval_status === "PENDING").length,
    [products]
  );
  const approvedCount = useMemo(
    () => products.filter((p) => p.approval_status === "APPROVED").length,
    [products]
  );
  const rejectedCount = useMemo(
    () => products.filter((p) => p.approval_status === "REJECTED").length,
    [products]
  );

  const filteredProducts = useMemo(() => {
    return products.filter((item) => {
      // Tab filter
      if (activeTab === "PENDING" && item.approval_status !== "PENDING") return false;
      if (activeTab === "APPROVED" && item.approval_status !== "APPROVED") return false;
      if (activeTab === "REJECTED" && item.approval_status !== "REJECTED") return false;

      // Search filter
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesId = item.product_id?.toLowerCase().includes(query);
        const matchesName = item.name?.toLowerCase().includes(query);
        const matchesCategory = item.category?.toLowerCase().includes(query);
        const matchesSupplier = item.supplier_id?.toLowerCase().includes(query);
        if (!matchesId && !matchesName && !matchesCategory && !matchesSupplier) {
          return false;
        }
      }
      return true;
    });
  }, [products, activeTab, searchQuery]);

  if (loading) return <Loading message="Loading products portfolio..." />;

  return (
    <div className="page-container">
      {/* Page Heading */}
      <section className="page-heading">
        <div>
          <p className="page-eyebrow">
            {isSupplier ? "SUPPLIER PRODUCTS & OFFERS" : "CATALOG & APPROVAL WORKFLOW"}
          </p>
          <h1>{isSupplier ? "My Products" : "Product Catalog & Approvals"}</h1>
          <p style={{ color: "var(--text)", fontSize: "14px", marginTop: "4px" }}>
            {isSupplier
              ? "Add products to your catalog. Once approved by a Supply Chain Manager or Administrator, you can create supply offers directly on them."
              : "Review supplier product submissions, approve or reject catalog additions, and manage active products."}
          </p>
        </div>
      </section>

      {/* Notifications */}
      {error && <ErrorMessage title="Products error" message={error} onRetry={loadProducts} />}

      {successMsg && (
        <div className="success-banner" style={{ marginBottom: "20px" }}>
          <span style={{ fontSize: "18px" }}>✓</span>
          <strong>{successMsg}</strong>
        </div>
      )}

      {/* Workflow banner for Supplier */}
      {isSupplier && (
        <section
          style={{
            background: "linear-gradient(135deg, rgba(212, 175, 55, 0.08) 0%, rgba(26, 26, 26, 0.6) 100%)",
            border: "1px solid rgba(212, 175, 55, 0.25)",
            borderRadius: "10px",
            padding: "16px 20px",
            marginBottom: "24px",
            display: "flex",
            flexWrap: "wrap",
            gap: "16px",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div>
            <span
              style={{
                fontSize: "11px",
                fontWeight: 700,
                letterSpacing: "0.08em",
                color: "var(--accent)",
                textTransform: "uppercase",
              }}
            >
              Approval Workflow
            </span>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginTop: "6px", flexWrap: "wrap" }}>
              <span style={{ color: "#F5F5F5", fontSize: "13px", fontWeight: 600 }}>1. Submit Product</span>
              <span style={{ color: "var(--text)", fontSize: "13px" }}>➔</span>
              <span style={{ color: "#F5F5F5", fontSize: "13px", fontWeight: 600 }}>2. Manager / Admin Reviews</span>
              <span style={{ color: "var(--text)", fontSize: "13px" }}>➔</span>
              <span style={{ color: "#22c55e", fontSize: "13px", fontWeight: 600 }}>
                3. Create Offers on Approved Products
              </span>
            </div>
          </div>
          <div style={{ fontSize: "12px", color: "var(--text)" }}>
            Need help? Products must be <strong>Approved</strong> before supply contracts & offers can be submitted.
          </div>
        </section>
      )}

      {/* Add Product Form: available to Supplier & Admin/Manager */}
      <section className="investigation-card" style={{ marginBottom: "24px" }}>
        <div className="section-header">
          <div>
            <span className="section-eyebrow">
              {isSupplier ? "SUBMIT PRODUCT" : "CATALOG MANAGEMENT"}
            </span>
            <h2>{isSupplier ? "Add New Product for Approval" : "Add Product"}</h2>
          </div>
          {isSupplier && (
            <span
              style={{
                fontSize: "12px",
                background: "rgba(234, 179, 8, 0.15)",
                color: "#eab308",
                padding: "4px 10px",
                borderRadius: "20px",
                fontWeight: 600,
              }}
            >
              Starts as Pending Approval
            </span>
          )}
        </div>

        <form onSubmit={handleCreateProduct} className="form-grid">
          <div className="form-field">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
              <label style={{ margin: 0 }}>Product ID</label>
              <span
                style={{
                  fontSize: "11px",
                  color: "var(--accent)",
                  fontWeight: 600,
                  background: "rgba(212, 175, 55, 0.12)",
                  padding: "2px 8px",
                  borderRadius: "4px",
                  border: "1px solid rgba(212, 175, 55, 0.25)",
                }}
              >
                ✨ Auto-Generated
              </span>
            </div>
            <input
              className="search-input"
              value={autoProductId || "Generating ID..."}
              readOnly
              style={{
                backgroundColor: "rgba(255, 255, 255, 0.04)",
                color: "var(--accent)",
                fontWeight: 600,
                letterSpacing: "0.04em",
                cursor: "default",
              }}
              title="Product ID is automatically generated by the system"
            />
          </div>

          <div className="form-field">
            <label>Product Name *</label>
            <input
              className="search-input"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="e.g. High Density Battery Pack"
              required
            />
          </div>

          <div className="form-field">
            <label>Category *</label>
            <input
              className="search-input"
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              placeholder="e.g. Energy Storage"
              required
            />
          </div>

          <div className="form-field">
            <label>Base Unit Cost ($) *</label>
            <input
              className="search-input"
              type="number"
              step="0.01"
              min="0"
              value={form.unit_cost}
              onChange={(e) => setForm({ ...form, unit_cost: e.target.value })}
              placeholder="e.g. 150.00"
              required
            />
          </div>

          {isAdminOrManager && (
            <div className="form-field">
              <label>Supplier ID (Optional)</label>
              <input
                className="search-input"
                value={form.supplier_id}
                onChange={(e) => setForm({ ...form, supplier_id: e.target.value })}
                placeholder="e.g. S001 (Blank for Catalog)"
              />
            </div>
          )}

          <div className="form-field">
            <label>Initial Status</label>
            <select
              className="search-input"
              value={form.status}
              onChange={(e) => setForm({ ...form, status: e.target.value })}
            >
              <option value="ACTIVE">ACTIVE</option>
              <option value="INACTIVE">INACTIVE</option>
            </select>
          </div>

          <div className="form-field" style={{ justifyContent: "flex-end" }}>
            <button
              type="submit"
              className="primary-button"
              disabled={submittingProduct}
              style={{ height: "42px", width: "100%" }}
            >
              {submittingProduct
                ? "Submitting..."
                : isSupplier
                ? "Submit for Approval"
                : "Create Product"}
            </button>
          </div>
        </form>
      </section>

      {/* Filter Tabs & Search Bar */}
      <section
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "12px",
          marginBottom: "16px",
        }}
      >
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          <button
            onClick={() => setActiveTab("ALL")}
            className="secondary-button"
            style={{
              padding: "6px 14px",
              fontSize: "13px",
              borderColor: activeTab === "ALL" ? "var(--accent)" : "var(--border)",
              color: activeTab === "ALL" ? "var(--accent)" : "var(--text)",
              backgroundColor: activeTab === "ALL" ? "rgba(212, 175, 55, 0.12)" : "transparent",
            }}
          >
            All Products ({products.length})
          </button>

          <button
            onClick={() => setActiveTab("PENDING")}
            className="secondary-button"
            style={{
              padding: "6px 14px",
              fontSize: "13px",
              borderColor: activeTab === "PENDING" ? "#eab308" : "var(--border)",
              color: activeTab === "PENDING" ? "#eab308" : "var(--text)",
              backgroundColor: activeTab === "PENDING" ? "rgba(234, 179, 8, 0.15)" : "transparent",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            Pending Review
            {pendingCount > 0 && (
              <span
                style={{
                  background: "#eab308",
                  color: "#000",
                  padding: "1px 6px",
                  borderRadius: "10px",
                  fontSize: "11px",
                  fontWeight: 700,
                }}
              >
                {pendingCount}
              </span>
            )}
          </button>

          <button
            onClick={() => setActiveTab("APPROVED")}
            className="secondary-button"
            style={{
              padding: "6px 14px",
              fontSize: "13px",
              borderColor: activeTab === "APPROVED" ? "#22c55e" : "var(--border)",
              color: activeTab === "APPROVED" ? "#22c55e" : "var(--text)",
              backgroundColor: activeTab === "APPROVED" ? "rgba(34, 197, 94, 0.15)" : "transparent",
            }}
          >
            Approved ({approvedCount})
          </button>

          <button
            onClick={() => setActiveTab("REJECTED")}
            className="secondary-button"
            style={{
              padding: "6px 14px",
              fontSize: "13px",
              borderColor: activeTab === "REJECTED" ? "#ef4444" : "var(--border)",
              color: activeTab === "REJECTED" ? "#ef4444" : "var(--text)",
              backgroundColor: activeTab === "REJECTED" ? "rgba(239, 68, 68, 0.15)" : "transparent",
            }}
          >
            Rejected ({rejectedCount})
          </button>
        </div>

        <div style={{ minWidth: "260px" }}>
          <input
            className="search-input"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by ID, name, or category..."
            style={{ height: "36px", fontSize: "13px" }}
          />
        </div>
      </section>

      {/* Table Section */}
      <section className="data-table-wrapper">
        {filteredProducts.length === 0 ? (
          <EmptyState
            title="No products found"
            message={
              searchQuery
                ? "No products match your search query."
                : activeTab !== "ALL"
                ? `No products currently have status: ${activeTab}.`
                : isSupplier
                ? "You haven't submitted any products yet. Use the form above to add your first product."
                : "There are currently no products registered in the catalog."
            }
          />
        ) : (
          <table className="risk-table">
            <thead>
              <tr>
                <th>Product ID</th>
                <th>Name</th>
                <th>Category</th>
                <th>Unit Cost</th>
                {isAdminOrManager && <th>Supplier</th>}
                <th>Status</th>
                <th>Approval</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredProducts.map((product) => {
                const isApproved = product.approval_status === "APPROVED";
                const isPending = product.approval_status === "PENDING";
                const isRejected = product.approval_status === "REJECTED";

                return (
                  <tr key={product.product_id}>
                    <td>
                      <code style={{ fontSize: "12px", color: "var(--accent)" }}>
                        {product.product_id}
                      </code>
                    </td>
                    <td style={{ fontWeight: 600 }}>{product.name}</td>
                    <td>{product.category}</td>
                    <td>${Number(product.unit_cost || 0).toFixed(2)}</td>

                    {isAdminOrManager && (
                      <td>
                        {product.supplier_id ? (
                          <span
                            style={{
                              background: "rgba(59, 130, 246, 0.15)",
                              color: "#60a5fa",
                              padding: "2px 8px",
                              borderRadius: "4px",
                              fontSize: "12px",
                              fontWeight: 600,
                            }}
                          >
                            {product.supplier_id}
                          </span>
                        ) : (
                          <span style={{ color: "var(--text)", fontSize: "12px" }}>Catalog</span>
                        )}
                      </td>
                    )}

                    <td>
                      <span
                        style={{
                          display: "inline-block",
                          padding: "2px 8px",
                          borderRadius: "4px",
                          fontSize: "11px",
                          fontWeight: "600",
                          backgroundColor:
                            product.status === "ACTIVE"
                              ? "rgba(34, 197, 94, 0.15)"
                              : "rgba(100, 116, 139, 0.2)",
                          color: product.status === "ACTIVE" ? "#22c55e" : "#94a3b8",
                        }}
                      >
                        {product.status}
                      </span>
                    </td>

                    <td>
                      {isApproved && (
                        <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                          <span
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px",
                              padding: "3px 8px",
                              borderRadius: "4px",
                              fontSize: "12px",
                              fontWeight: "600",
                              backgroundColor: "rgba(34, 197, 94, 0.15)",
                              color: "#22c55e",
                              width: "fit-content",
                            }}
                          >
                            ✓ Approved
                          </span>
                          {product.approved_by && (
                            <span style={{ fontSize: "10px", color: "var(--text)" }}>
                              by {product.approved_by}
                            </span>
                          )}
                        </div>
                      )}

                      {isPending && (
                        <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                          <span
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px",
                              padding: "3px 8px",
                              borderRadius: "4px",
                              fontSize: "12px",
                              fontWeight: "600",
                              backgroundColor: "rgba(234, 179, 8, 0.15)",
                              color: "#eab308",
                              width: "fit-content",
                            }}
                          >
                            ⏳ Pending Review
                          </span>
                          <span style={{ fontSize: "10px", color: "var(--text)" }}>
                            Awaiting Manager/Admin
                          </span>
                        </div>
                      )}

                      {isRejected && (
                        <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                          <span
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px",
                              padding: "3px 8px",
                              borderRadius: "4px",
                              fontSize: "12px",
                              fontWeight: "600",
                              backgroundColor: "rgba(239, 68, 68, 0.15)",
                              color: "#ef4444",
                              width: "fit-content",
                            }}
                          >
                            ✕ Rejected
                          </span>
                          {product.rejection_reason && (
                            <span
                              style={{
                                fontSize: "10px",
                                color: "#f87171",
                                maxWidth: "160px",
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "nowrap",
                              }}
                              title={product.rejection_reason}
                            >
                              Reason: {product.rejection_reason}
                            </span>
                          )}
                        </div>
                      )}
                    </td>

                    <td>
                      <div style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap" }}>
                        {/* Supplier actions */}
                        {isSupplier && (
                          <>
                            {isApproved ? (
                              <button
                                className="primary-button"
                                style={{
                                  padding: "6px 12px",
                                  fontSize: "12px",
                                  height: "32px",
                                  background: "var(--accent)",
                                  color: "#000",
                                  fontWeight: 700,
                                }}
                                onClick={() => handleOpenOfferModal(product)}
                              >
                                + Create Offer
                              </button>
                            ) : isPending ? (
                              <span
                                style={{
                                  fontSize: "11px",
                                  color: "#eab308",
                                  background: "rgba(234, 179, 8, 0.1)",
                                  padding: "4px 8px",
                                  borderRadius: "4px",
                                  border: "1px dashed rgba(234, 179, 8, 0.3)",
                                }}
                                title="Offers can only be created once the product is approved by a manager or admin."
                              >
                                🔒 Locked (Awaiting Approval)
                              </span>
                            ) : (
                              <span
                                style={{
                                  fontSize: "11px",
                                  color: "#ef4444",
                                  background: "rgba(239, 68, 68, 0.1)",
                                  padding: "4px 8px",
                                  borderRadius: "4px",
                                }}
                              >
                                ✕ Cannot Offer
                              </span>
                            )}
                          </>
                        )}

                        {/* Manager & Admin actions for approval */}
                        {isAdminOrManager && (
                          <>
                            {isPending && (
                              <>
                                <button
                                  className="primary-button"
                                  style={{
                                    padding: "4px 10px",
                                    fontSize: "12px",
                                    height: "30px",
                                    backgroundColor: "#10b981",
                                    borderColor: "#10b981",
                                    color: "#fff",
                                  }}
                                  onClick={() => handleApprove(product.product_id)}
                                >
                                  ✓ Approve
                                </button>
                                <button
                                  className="secondary-button"
                                  style={{
                                    padding: "4px 10px",
                                    fontSize: "12px",
                                    height: "30px",
                                    color: "#ef4444",
                                    borderColor: "rgba(239, 68, 68, 0.5)",
                                  }}
                                  onClick={() => handleOpenRejectModal(product)}
                                >
                                  ✕ Reject
                                </button>
                              </>
                            )}

                            {/* Additional admin actions */}
                            {isAdmin && (
                              <>
                                <button
                                  className="secondary-button"
                                  style={{ padding: "4px 8px", fontSize: "11px", height: "30px" }}
                                  onClick={() => handleToggleStatus(product)}
                                >
                                  Toggle
                                </button>
                                <button
                                  className="secondary-button"
                                  style={{
                                    padding: "4px 8px",
                                    fontSize: "11px",
                                    height: "30px",
                                    color: "#ef4444",
                                  }}
                                  onClick={() => handleDelete(product.product_id)}
                                >
                                  Delete
                                </button>
                              </>
                            )}
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>

      {/* ========================================================= */}
      {/* MODAL: Create Offer on Approved Product (for Supplier)    */}
      {/* ========================================================= */}
      {offerProduct && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0, 0, 0, 0.78)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
          }}
        >
          <div
            className="investigation-card"
            style={{
              width: "100%",
              maxWidth: "520px",
              border: "1px solid rgba(212, 175, 55, 0.5)",
              boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.7)",
              background: "#121212",
              padding: "24px",
              borderRadius: "12px",
            }}
          >
            <div className="section-header" style={{ marginBottom: "16px" }}>
              <div>
                <span className="section-eyebrow">CREATE SUPPLY OFFER</span>
                <h2 style={{ fontSize: "20px", marginTop: "2px" }}>Offer for {offerProduct.name}</h2>
              </div>
              <button
                type="button"
                className="secondary-button"
                style={{ padding: "4px 8px", height: "30px" }}
                onClick={() => setOfferProduct(null)}
              >
                ✕
              </button>
            </div>

            <div
              style={{
                background: "rgba(255, 255, 255, 0.03)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                padding: "12px 14px",
                marginBottom: "20px",
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "10px",
                fontSize: "13px",
              }}
            >
              <div>
                <span style={{ color: "var(--text)", display: "block", fontSize: "11px" }}>Product ID</span>
                <code style={{ color: "var(--accent)" }}>{offerProduct.product_id}</code>
              </div>
              <div>
                <span style={{ color: "var(--text)", display: "block", fontSize: "11px" }}>Category</span>
                <span style={{ color: "#fff" }}>{offerProduct.category}</span>
              </div>
              <div>
                <span style={{ color: "var(--text)", display: "block", fontSize: "11px" }}>Approval Status</span>
                <span style={{ color: "#22c55e", fontWeight: 600 }}>✓ Approved</span>
              </div>
              <div>
                <span style={{ color: "var(--text)", display: "block", fontSize: "11px" }}>Base Cost</span>
                <span style={{ color: "#fff" }}>${Number(offerProduct.unit_cost || 0).toFixed(2)}</span>
              </div>
            </div>

            {offerError && (
              <div style={{ marginBottom: "16px" }}>
                <ErrorMessage title="Offer Creation Failed" message={offerError} />
              </div>
            )}

            <form onSubmit={handleCreateOfferSubmit}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px", marginBottom: "16px" }}>
                <div>
                  <label style={{ fontSize: "12px", color: "var(--text)", display: "block", marginBottom: "4px" }}>
                    Offer Quantity *
                  </label>
                  <input
                    className="search-input"
                    type="number"
                    min="1"
                    value={offerForm.quantity}
                    onChange={(e) => setOfferForm({ ...offerForm, quantity: e.target.value })}
                    placeholder="e.g. 100"
                    required
                  />
                </div>

                <div>
                  <label style={{ fontSize: "12px", color: "var(--text)", display: "block", marginBottom: "4px" }}>
                    Offer Unit Price ($) *
                  </label>
                  <input
                    className="search-input"
                    type="number"
                    step="0.01"
                    min="0"
                    value={offerForm.unit_price}
                    onChange={(e) => setOfferForm({ ...offerForm, unit_price: e.target.value })}
                    placeholder="e.g. 145.00"
                    required
                  />
                </div>

                <div>
                  <label style={{ fontSize: "12px", color: "var(--text)", display: "block", marginBottom: "4px" }}>
                    Delivery Lead Time (Days) *
                  </label>
                  <input
                    className="search-input"
                    type="number"
                    min="1"
                    value={offerForm.delivery_days}
                    onChange={(e) => setOfferForm({ ...offerForm, delivery_days: e.target.value })}
                    placeholder="e.g. 7"
                    required
                  />
                </div>

                <div>
                  <label style={{ fontSize: "12px", color: "var(--text)", display: "block", marginBottom: "4px" }}>
                    Offer Valid Until *
                  </label>
                  <input
                    className="search-input"
                    type="date"
                    value={offerForm.valid_until}
                    onChange={(e) => setOfferForm({ ...offerForm, valid_until: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setOfferProduct(null)}
                  disabled={offerSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="primary-button"
                  disabled={offerSubmitting}
                  style={{ minWidth: "140px" }}
                >
                  {offerSubmitting ? "Submitting Offer..." : "Submit Offer"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* MODAL: Reject Product Proposal (for Manager & Admin)      */}
      {/* ========================================================= */}
      {rejectingProduct && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0, 0, 0, 0.78)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
          }}
        >
          <div
            className="investigation-card"
            style={{
              width: "100%",
              maxWidth: "460px",
              border: "1px solid rgba(239, 68, 68, 0.5)",
              boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.7)",
              background: "#121212",
              padding: "24px",
              borderRadius: "12px",
            }}
          >
            <div className="section-header" style={{ marginBottom: "16px" }}>
              <div>
                <span className="section-eyebrow" style={{ color: "#ef4444" }}>
                  REJECT PRODUCT
                </span>
                <h2 style={{ fontSize: "18px", marginTop: "2px" }}>
                  Reject {rejectingProduct.name} ({rejectingProduct.product_id})
                </h2>
              </div>
              <button
                type="button"
                className="secondary-button"
                style={{ padding: "4px 8px", height: "30px" }}
                onClick={() => setRejectingProduct(null)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleConfirmReject}>
              <div style={{ marginBottom: "16px" }}>
                <label style={{ fontSize: "12px", color: "var(--text)", display: "block", marginBottom: "6px" }}>
                  Reason for rejection (will be visible to the supplier):
                </label>
                <textarea
                  className="search-input"
                  style={{ width: "100%", minHeight: "90px", resize: "vertical" }}
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="e.g. Unit cost exceeds benchmark or duplicate product specification..."
                  required
                />
              </div>

              <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setRejectingProduct(null)}
                  disabled={rejectSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="primary-button"
                  disabled={rejectSubmitting}
                  style={{
                    backgroundColor: "#ef4444",
                    borderColor: "#ef4444",
                    color: "#fff",
                  }}
                >
                  {rejectSubmitting ? "Rejecting..." : "Confirm Rejection"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default ProductsPage;
