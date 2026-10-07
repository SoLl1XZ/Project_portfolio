// Renders one card per project from window.PORTFOLIO_DATA, which build.py writes to data/projects.js.
// All project text is inserted with textContent, never innerHTML, so text from a README can't run as code.

// Dates like "2026-10-07" are parsed as UTC midnight; formatting in UTC keeps them from showing the day before.
const DAY_FORMAT = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
const BUILD_TIME_FORMAT = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" });

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderTags(tags) {
  const list = element("ul", "tags");
  list.setAttribute("aria-label", "Technologies");
  for (const tag of tags) list.append(element("li", "tag", tag));
  return list;
}

function renderFooter(project) {
  const footer = element("footer", "card-footer");
  const updated = element("time", "updated", `Updated ${DAY_FORMAT.format(new Date(project.updated))}`);
  updated.dateTime = project.updated;
  footer.append(updated);
  for (const [label, url] of Object.entries(project.links)) {
    const link = element("a", "card-link", label);
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener";
    footer.append(link);
  }
  return footer;
}

function renderCard(project) {
  const card = element("article", "card");
  card.append(element("h3", "card-title", project.title));
  if (project.description) card.append(element("p", "card-description", project.description));
  if (project.tags.length) card.append(renderTags(project.tags));
  card.append(renderFooter(project));
  return card;
}

function renderPortfolio(data) {
  const grid = document.getElementById("projects");
  if (!data) {
    grid.append(element("p", "message", "No project data found. Run `python3 build.py` to generate it."));
    return;
  }
  const { projects, generated } = data;
  document.getElementById("project-count").textContent = `${projects.length} ${projects.length === 1 ? "project" : "projects"}`;
  document.getElementById("generated").textContent = `Last built ${BUILD_TIME_FORMAT.format(new Date(generated))}`;
  if (projects.length === 0) {
    grid.append(element("p", "message", "No projects yet."));
    return;
  }
  grid.append(...projects.map(renderCard));
}

renderPortfolio(window.PORTFOLIO_DATA);
