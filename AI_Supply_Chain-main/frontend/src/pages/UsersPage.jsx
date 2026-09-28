import { useEffect, useState } from "react";

import {
  getUsers,
  createUser,
  updateUser,
  deleteUser,
} from "../api/usersApi";

import Loading from "../components/Loading";
import ErrorMessage from "../components/ErrorMessage";
import EmptyState from "../components/EmptyState";


function getErrorMessage(err, fallback = "Something went wrong.") {
  const detail = err?.response?.data?.detail;

  // FastAPI validation error
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }

        if (item?.msg) {
          const location = Array.isArray(item.loc)
            ? item.loc.filter((value) => value !== "body").join(" → ")
            : "";

          return location
            ? `${location}: ${item.msg}`
            : item.msg;
        }

        return "Validation error";
      })
      .join(" | ");
  }

  // Normal FastAPI HTTPException
  if (typeof detail === "string") {
    return detail;
  }

  // Other API error
  if (typeof err?.message === "string") {
    return err.message;
  }

  return fallback;
}


function UsersPage({ auth }) {
  const [users, setUsers] = useState([]);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");

  const [successMsg, setSuccessMsg] = useState("");

  const [submitting, setSubmitting] = useState(false);


  // =========================================================
  // CREATE USER FORM
  // =========================================================

  const emptyForm = {
    username: "",
    email: "",
    name: "",
    password: "",
    role: "SUPPLIER",
  };

  const [form, setForm] = useState(emptyForm);


  // =========================================================
  // LOAD USERS
  // =========================================================

  const loadUsers = async () => {
    try {
      setLoading(true);
      setError("");

      const data = await getUsers();

      setUsers(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(
        getErrorMessage(
          err,
          "Unable to load users."
        )
      );
    } finally {
      setLoading(false);
    }
  };


  // =========================================================
  // INITIAL LOAD
  // =========================================================

  useEffect(() => {
    loadUsers();
  }, []);


  // =========================================================
  // FORM CHANGE
  // =========================================================

  const handleChange = (event) => {
    const { name, value } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));
  };


  // =========================================================
  // CREATE USER
  // =========================================================

  const handleSubmit = async (event) => {
    event.preventDefault();

    try {
      setError("");
      setSuccessMsg("");
      setSubmitting(true);

      // IMPORTANT:
      // supplier_id is intentionally NOT sent.
      //
      // Backend automatically generates:
      // S001
      // S002
      // S003
      // ...

      await createUser({
        username: form.username.trim(),
        email: form.email.trim(),
        name: form.name.trim(),
        password: form.password,
        role: form.role,
      });

      setForm(emptyForm);

      setSuccessMsg(
        form.role === "SUPPLIER"
          ? "Supplier user created successfully. Supplier ID was generated automatically."
          : "User created successfully."
      );

      await loadUsers();

    } catch (err) {
      setError(
        getErrorMessage(
          err,
          "Unable to create user."
        )
      );
    } finally {
      setSubmitting(false);
    }
  };


  // =========================================================
  // TOGGLE USER STATUS
  // =========================================================

  const handleToggleStatus = async (user) => {
    try {
      setError("");
      setSuccessMsg("");

      const nextStatus =
        user.status === "ACTIVE"
          ? "INACTIVE"
          : "ACTIVE";

      await updateUser(user.id, {
        status: nextStatus,
      });

      setSuccessMsg(
        `User ${user.username} status changed to ${nextStatus}.`
      );

      await loadUsers();

    } catch (err) {
      setError(
        getErrorMessage(
          err,
          "Unable to update user status."
        )
      );
    }
  };


  // =========================================================
  // DELETE USER
  // =========================================================

  const handleDelete = async (user) => {
    const confirmed = window.confirm(
      `Are you sure you want to delete user "${user.username}"?`
    );

    if (!confirmed) {
      return;
    }

    try {
      setError("");
      setSuccessMsg("");

      await deleteUser(user.id);

      setSuccessMsg(
        `User #${user.id} deleted successfully.`
      );

      await loadUsers();

    } catch (err) {
      setError(
        getErrorMessage(
          err,
          "Unable to delete user."
        )
      );
    }
  };


  // =========================================================
  // LOADING
  // =========================================================

  if (loading) {
    return (
      <Loading message="Loading users..." />
    );
  }


  // =========================================================
  // PAGE
  // =========================================================

  return (
    <div className="page-container">

      {/* =====================================================
          PAGE HEADER
      ====================================================== */}

      <section className="page-heading">
        <div>
          <p className="page-eyebrow">
            USER ADMINISTRATION
          </p>

          <h1>
            Users
          </h1>
        </div>
      </section>


      {/* =====================================================
          ERROR MESSAGE
      ====================================================== */}

      {error && (
        <ErrorMessage
          title="Users Error"
          message={error}
          onRetry={loadUsers}
        />
      )}


      {/* =====================================================
          SUCCESS MESSAGE
      ====================================================== */}

      {successMsg && (
        <div
          className="system-card"
          style={{
            marginBottom: "16px",
            borderColor:
              "rgba(34, 197, 94, 0.4)",
            background:
              "rgba(34, 197, 94, 0.08)",
          }}
        >
          <strong
            style={{
              color: "#22c55e",
            }}
          >
            {successMsg}
          </strong>
        </div>
      )}


      {/* =====================================================
          CREATE USER
      ====================================================== */}

      <section
        className="investigation-card"
        style={{
          marginBottom: "20px",
        }}
      >

        <div className="section-header">
          <div>

            <span className="section-eyebrow">
              CREATE USER
            </span>

            <h2>
              Add user
            </h2>

          </div>
        </div>


        <form
          onSubmit={handleSubmit}
          style={{
            display: "grid",
            gridTemplateColumns:
              "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "12px",
            alignItems: "end",
          }}
        >

          {/* USERNAME */}

          <div>
            <label
              style={{
                fontSize: "12px",
                opacity: 0.8,
                display: "block",
                marginBottom: "4px",
              }}
            >
              Username
            </label>

            <input
              className="search-input"
              name="username"
              value={form.username}
              onChange={handleChange}
              placeholder="Username"
              minLength={3}
              required
            />
          </div>


          {/* EMAIL */}

          <div>
            <label
              style={{
                fontSize: "12px",
                opacity: 0.8,
                display: "block",
                marginBottom: "4px",
              }}
            >
              Email
            </label>

            <input
              className="search-input"
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              placeholder="Email"
              required
            />
          </div>


          {/* NAME */}

          <div>
            <label
              style={{
                fontSize: "12px",
                opacity: 0.8,
                display: "block",
                marginBottom: "4px",
              }}
            >
              Name
            </label>

            <input
              className="search-input"
              name="name"
              value={form.name}
              onChange={handleChange}
              placeholder="Full name"
              required
            />
          </div>


          {/* PASSWORD */}

          <div>
            <label
              style={{
                fontSize: "12px",
                opacity: 0.8,
                display: "block",
                marginBottom: "4px",
              }}
            >
              Password
            </label>

            <input
              className="search-input"
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              placeholder="Password"
              minLength={6}
              required
            />
          </div>


          {/* ROLE */}

          <div>
            <label
              style={{
                fontSize: "12px",
                opacity: 0.8,
                display: "block",
                marginBottom: "4px",
              }}
            >
              Role
            </label>

            <select
              className="search-input"
              name="role"
              value={form.role}
              onChange={handleChange}
            >
              <option value="ADMIN">
                ADMIN
              </option>

              <option value="SUPPLY_CHAIN_MANAGER">
                SUPPLY_CHAIN_MANAGER
              </option>

              <option value="SUPPLIER">
                SUPPLIER
              </option>
            </select>
          </div>


          {/* CREATE BUTTON */}

          <div>

            <button
              type="submit"
              className="primary-button"
              disabled={submitting}
              style={{
                width: "100%",
              }}
            >
              {submitting
                ? "Creating..."
                : "Create User"}
            </button>

          </div>

        </form>


        {/* SUPPLIER ID INFORMATION */}

        {form.role === "SUPPLIER" && (
          <div
            style={{
              marginTop: "14px",
              padding: "10px 12px",
              borderRadius: "6px",
              background:
                "rgba(59, 130, 246, 0.08)",
              border:
                "1px solid rgba(59, 130, 246, 0.25)",
              fontSize: "13px",
              opacity: 0.9,
            }}
          >
            Supplier ID will be generated
            automatically by the system.
          </div>
        )}

      </section>


      {/* =====================================================
          USERS TABLE
      ====================================================== */}

      <section className="data-table-wrapper">

        {users.length === 0 ? (

          <EmptyState
            title="No users"
            message="There are currently no users found."
          />

        ) : (

          <table className="risk-table">

            <thead>

              <tr>

                <th>
                  ID
                </th>

                <th>
                  Username
                </th>

                <th>
                  Name
                </th>

                <th>
                  Role
                </th>

                <th>
                  Supplier ID
                </th>

                <th>
                  Status
                </th>

                <th>
                  Actions
                </th>

              </tr>

            </thead>


            <tbody>

              {users.map((user) => (

                <tr key={user.id}>

                  {/* ID */}

                  <td>
                    #{user.id}
                  </td>


                  {/* USERNAME */}

                  <td>
                    {user.username}
                  </td>


                  {/* NAME */}

                  <td>
                    {user.name || "-"}
                  </td>


                  {/* ROLE */}

                  <td>
                    {user.role}
                  </td>


                  {/* SUPPLIER ID */}

                  <td>

                    {user.role === "SUPPLIER"
                      ? (
                        <span
                          style={{
                            fontWeight: "600",
                          }}
                        >
                          {user.supplier_id || "-"}
                        </span>
                      )
                      : (
                        <span
                          style={{
                            opacity: 0.5,
                          }}
                        >
                          -
                        </span>
                      )}

                  </td>


                  {/* STATUS */}

                  <td>

                    <span
                      style={{
                        display:
                          "inline-block",

                        padding:
                          "2px 8px",

                        borderRadius:
                          "4px",

                        fontSize:
                          "12px",

                        fontWeight:
                          "600",

                        backgroundColor:
                          user.status === "ACTIVE"
                            ? "rgba(34, 197, 94, 0.15)"
                            : "rgba(239, 68, 68, 0.15)",

                        color:
                          user.status === "ACTIVE"
                            ? "#22c55e"
                            : "#ef4444",
                      }}
                    >
                      {user.status || "ACTIVE"}
                    </span>

                  </td>


                  {/* ACTIONS */}

                  <td>

                    <button
                      className="secondary-button"
                      style={{
                        marginRight: "8px",
                      }}
                      onClick={() =>
                        handleToggleStatus(user)
                      }
                    >
                      Toggle
                    </button>


                    <button
                      className="secondary-button"
                      onClick={() =>
                        handleDelete(user)
                      }
                    >
                      Delete
                    </button>

                  </td>

                </tr>

              ))}

            </tbody>

          </table>

        )}

      </section>

    </div>
  );
}


export default UsersPage;
