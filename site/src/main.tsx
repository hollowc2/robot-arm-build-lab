import React, { useMemo } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/archivo/wdth.css";
import "@fontsource-variable/jetbrains-mono";
import { PartsExplorer } from "./PartsExplorer";
import { type Catalog, generatedBase, type ProgressFeed, repoUrl, useJson } from "./shared";
import { Simulator, type TitleBlockFact } from "./Simulator";
import "./styles.css";

const designDecisionModules = import.meta.glob("../../content/design-decisions/*.md", {
  query: "?raw",
  import: "default",
  eager: true,
});

function parseNote(raw: unknown, path: string) {
  const text = String(raw);
  const title = text.match(/^#\s+(.+)$/m)?.[1] ?? path.split("/").pop() ?? "Note";
  const paragraphs = text.replace(/^#\s+.+$/m, "").trim().split(/\n\s*\n/);
  return { title, paragraphs, path };
}

const jointSpecs = [
  { id: "J1", name: "Base yaw", range: "360°", ratio: "6:1", motor: "NEMA 17", drive: "20T → 120T herringbone gear" },
  { id: "J2", name: "Shoulder", range: "±125°", ratio: "5:1", motor: "NEMA 17", drive: "16T → 80T HTD 3M belt" },
  { id: "J3", name: "Elbow", range: "±135°", ratio: "3.75:1", motor: "NEMA 17", drive: "16T → 60T HTD 3M belt" },
  { id: "J4", name: "Wrist pitch", range: "−150° / +18°", ratio: "1.6:1", motor: "28BYJ-48", drive: "20T → 32T HTD 3M belt" },
  { id: "J5", name: "Gripper", range: "0–24 mm", ratio: "1:1", motor: "SG90 servo", drive: "Servo horn → parallel jaws" },
];

const buildSteps = [
  { title: "Sketch", body: "A spoken or sketched mechanical idea becomes a short design note." },
  { title: "Prompt", body: "The note turns into an LLM-assisted CAD prompt on its own branch." },
  { title: "Code", body: "Every part is Python build123d source, with regression tests for fit." },
  { title: "Build", body: "CI regenerates the STEP and STL exports and refreshes this page." },
  { title: "Print", body: "PETG prints get fit-checked on the bench before the next revision." },
];

function ArmMark() {
  return (
    <svg className="arm-mark" viewBox="0 0 32 32" aria-hidden="true">
      <path d="M5 28h14" />
      <path d="M12 28v-4l-1-7 9-8 6 4" />
      <circle cx="11" cy="17" r="2.2" />
      <circle cx="20" cy="9" r="2.2" />
      <path d="M26 13l3 1M26 13l1 3" />
    </svg>
  );
}

function SectionHead({ index, title, lede }: { index: string; title: string; lede: string }) {
  return (
    <header className="section-head">
      <span className="section-index">{index}</span>
      <h2>{title}</h2>
      <p>{lede}</p>
    </header>
  );
}

function App() {
  const { data: catalog, error: catalogError } = useJson<Catalog>(`${generatedBase}/catalog.json`);
  const { data: progress } = useJson<ProgressFeed>(`${generatedBase}/progress.json`);
  const decisions = useMemo(
    () => Object.entries(designDecisionModules).map(([path, raw]) => parseNote(raw, path)).sort((a, b) => a.path.localeCompare(b.path)),
    [],
  );

  const parts = catalog?.parts ?? [];
  const partCount = parts.filter((part) => part.category !== "assembly").length;
  const printableCount = parts.filter((part) => part.printReady).length;
  const builtOn = catalog ? catalog.generatedAt.slice(0, 10) : "…";
  const commits = progress?.commits.slice(0, 6) ?? [];
  const facts: TitleBlockFact[] = [
    ["Drawing", "RA-01"],
    ["Axes", "4 + gripper"],
    ["Parts", catalog ? `${partCount} · ${printableCount} printable` : "…"],
    ["CAD build", builtOn],
    ["Rev", commits[0]?.sha ?? "main"],
  ];

  return (
    <>
      <header className="nav">
        <a className="brand" href="#simulator">
          <ArmMark />
          <span className="brand-code">RA-01</span>
          <span className="brand-name">Billy Bitcoin's Robot Arm</span>
        </a>
        <nav aria-label="Sections">
          <a href="#anatomy">Anatomy</a>
          <a href="#parts">Parts</a>
          <a href="#process">Process</a>
          <a href="#log">Log</a>
          <a className="nav-github" href={repoUrl} target="_blank" rel="noreferrer">GitHub ↗</a>
        </nav>
      </header>

      <main>
        <Simulator facts={facts}>
          <p className="kicker">Open source · 3D printed · Python CAD</p>
          <h1>
            <span className="h1-byline">Billy Bitcoin’s</span> <span className="h1-title">Robot <em>Arm</em></span>
          </h1>
          <p className="lede">
            A desktop arm where every printed part is generated from code. This is the real CAD assembly running live.
            Watch it build little brick models stud by stud, or grab a slider and take over.
          </p>
        </Simulator>

        <section className="section" id="anatomy">
          <SectionHead
            index="02"
            title="Anatomy"
            lede="Four stepper-driven joints and a servo gripper. The steppers work through printed gears and HTD 3M timing belts to trade speed for torque."
          />
          <ol className="joint-cards">
            {jointSpecs.map((spec) => (
              <li className="joint-card" key={spec.id}>
                <div className="joint-card-top">
                  <span className="tag">{spec.id}</span>
                  <span className="joint-range">{spec.range}</span>
                </div>
                <h3>{spec.name}</h3>
                <p className="joint-ratio">{spec.ratio}</p>
                <dl>
                  <div><dt>Motor</dt><dd>{spec.motor}</dd></div>
                  <div><dt>Drive</dt><dd>{spec.drive}</dd></div>
                </dl>
              </li>
            ))}
          </ol>
          <ul className="brains">
            <li><span>Motion + safety</span><strong>Arduino Uno R4</strong></li>
            <li><span>Interface</span><strong>ESP32, optional</strong></li>
            <li><span>Structure</span><strong>PETG, FDM printed</strong></li>
            <li><span>Payload target</span><strong>100 g</strong></li>
          </ul>
        </section>

        <section className="section" id="parts">
          <SectionHead
            index="03"
            title="Parts"
            lede="Every part is rebuilt from source whenever a change merges. Pick one to inspect it, download the STL, or read the code that made it."
          />
          {catalogError && <p className="data-warning">Part catalog not generated yet ({catalogError}).</p>}
          <PartsExplorer parts={parts} />
        </section>

        <section className="section" id="process">
          <SectionHead
            index="04"
            title="From idea to print"
            lede="Nothing here is drawn by hand. Parts are code, reviewed like code, and rebuilt by CI. A person approves every change."
          />
          <ol className="steps">
            {buildSteps.map((step, index) => (
              <li key={step.title}>
                <span className="step-index">{String(index + 1).padStart(2, "0")}</span>
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="section" id="log">
          <SectionHead index="05" title="Log" lede="Recent changes to the CAD, and the reasoning behind the bigger decisions." />
          <div className="log">
            <div>
              <h3 className="log-label">Recent commits</h3>
              <ol className="commits">
                {commits.map((commit) => (
                  <li key={commit.sha}>
                    <time dateTime={commit.date}>{commit.date}</time>
                    <a href={`${repoUrl}/commit/${commit.sha}`} target="_blank" rel="noreferrer">{commit.subject}</a>
                    <code>{commit.sha}</code>
                  </li>
                ))}
                {!commits.length && <li className="commits-empty">The commit feed has not been generated yet.</li>}
              </ol>
              <a className="text-link" href={`${repoUrl}/commits/main`} target="_blank" rel="noreferrer">Full history ↗</a>
            </div>
            <div>
              <h3 className="log-label">Design decisions</h3>
              <div className="notes">
                {decisions.map((note) => (
                  <details key={note.path}>
                    <summary>{note.title}</summary>
                    {note.paragraphs.map((paragraph) => <p key={paragraph.slice(0, 32)}>{paragraph}</p>)}
                  </details>
                ))}
              </div>
            </div>
          </div>
        </section>

        <aside className="safety">
          <p>
            <strong>Adult-supervised, not a toy.</strong> The motors stay unpowered around kids until the guards, interlocks,
            current limits, homing and a latching E-stop that cuts 12 V motor power all pass the{" "}
            <a href={`${repoUrl}/blob/main/content/safety-validation.md`} target="_blank" rel="noreferrer">safety checklist</a>.
          </p>
        </aside>
      </main>

      <footer className="footer">
        <span>RA-01 · Billy Bitcoin's Robot Arm Build Lab</span>
        <span>CAD generated {builtOn}</span>
        <a href={repoUrl} target="_blank" rel="noreferrer">Source on GitHub ↗</a>
      </footer>
    </>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
