import { useEffect, useState } from "react";
import { NavLink, useLocation, useOutlet } from "react-router";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { Menu, X } from "lucide-react";
import { GROUPS, SCREENS } from "../screens";
import ApiStatus from "./ApiStatus";
import { cx } from "./ui";

function Logo() {
  return (
    <NavLink to="/" className="flex items-center gap-3" aria-label="Meta-Fut A.I home">
      <img src="/favicon.svg" alt="" className="size-9" />
      <span className="font-display text-2xl font-bold uppercase leading-none tracking-wide">
        Meta-Fut <span className="text-turf">A.I</span>
      </span>
    </NavLink>
  );
}

function Navigation({ onNavigate }) {
  return (
    <nav aria-label="Main" className="flex flex-col gap-6">
      {GROUPS.map((group) => (
        <div key={group}>
          <p className="mb-2 px-3 text-[0.7rem] font-semibold uppercase tracking-[0.2em] text-fog">{group}</p>
          <ul className="flex flex-col gap-0.5">
            {SCREENS.filter((s) => s.group === group).map(({ path, title, icon: Icon }) => (
              <li key={path}>
                <NavLink to={path} end={path === "/"} onClick={onNavigate}
                  className={({ isActive }) => cx(
                    "flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
                    isActive ? "bg-turf/12 text-chalk ring-1 ring-turf/25" : "text-mist hover:bg-white/5 hover:text-chalk")}>
                  {({ isActive }) => (
                    <>
                      <Icon className={cx("size-4", isActive ? "text-turf" : "text-fog")} aria-hidden />
                      {title}
                    </>
                  )}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}

export default function Layout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  // Keep each page's own content while it fades out; <Outlet/> would already show the next page.
  const outlet = useOutlet();
  const reduce = useReducedMotion();
  useEffect(() => setMenuOpen(false), [location.pathname]);

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[17rem_minmax(0,1fr)]">
      {/* Sidebar on large screens */}
      <aside className="sticky top-0 hidden h-screen flex-col gap-8 overflow-y-auto border-r border-white/6 bg-pitch-900/70 px-4 py-6 backdrop-blur lg:flex">
        <div className="px-2"><Logo /></div>
        <Navigation />
        <p className="mt-auto px-3 text-xs leading-relaxed text-fog">Data: StatsBomb open data, 2015/16.</p>
      </aside>

      {/* Top bar on small screens */}
      <div className="sticky top-0 z-30 flex items-center justify-between border-b border-white/6 bg-pitch-900/90 px-4 py-3 backdrop-blur lg:hidden">
        <Logo />
        <button type="button" onClick={() => setMenuOpen((o) => !o)} aria-expanded={menuOpen} aria-label="Menu"
                className="rounded-xl p-2 text-mist hover:bg-white/6 hover:text-chalk">
          {menuOpen ? <X className="size-5" /> : <Menu className="size-5" />}
        </button>
      </div>
      <AnimatePresence>
        {menuOpen && (
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
                      className="fixed inset-x-0 top-[3.75rem] z-20 max-h-[calc(100vh-3.75rem)] overflow-y-auto border-b border-white/8 bg-pitch-900 px-4 py-5 lg:hidden">
            <Navigation onNavigate={() => setMenuOpen(false)} />
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex min-w-0 flex-col">
        <div className="flex items-center justify-end px-4 pt-4 sm:px-8">
          <ApiStatus />
        </div>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 pb-16 pt-4 sm:px-8">
          <AnimatePresence mode="wait">
            <motion.div key={location.pathname}
                        initial={reduce ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                        exit={reduce ? undefined : { opacity: 0 }} transition={{ duration: 0.2 }}>
              {outlet}
            </motion.div>
          </AnimatePresence>
        </main>
        <footer className="border-t border-white/6 px-4 py-5 text-xs text-fog sm:px-8">
          Meta-Fut A.I · Final Year Project, The University of Lahore · Data: StatsBomb open data (2015/16), non-commercial research use
        </footer>
      </div>
    </div>
  );
}
