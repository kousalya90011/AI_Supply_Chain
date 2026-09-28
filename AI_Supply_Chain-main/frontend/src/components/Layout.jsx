import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Header from "./Header";
import InteractiveBackground from "./InteractiveBackground";

function Layout({ auth, onLogout }) {
  return (
    <div className="app-layout">
      <InteractiveBackground />
      <Sidebar auth={auth} />

      <div className="main-area">
        <Header auth={auth} onLogout={onLogout} />

        <main className="page-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default Layout;
