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

function renderImage(project) {
  const image = element("img", "card-image");
  image.src = project.image;
  image.alt = `Screenshot of ${project.title}`;
  image.loading = "lazy";
  const [firstUrl] = Object.values(project.links);
  if (!firstUrl) return image;
  // The same link is in the footer, so this copy is hidden from keyboard and screen readers.
  const link = element("a", "card-image-link");
  link.href = firstUrl;
  link.target = "_blank";
  link.rel = "noopener";
  link.tabIndex = -1;
  link.setAttribute("aria-hidden", "true");
  link.append(image);
  return link;
}

function renderCard(project) {
  const card = element("article", project.image ? "card card-featured" : "card");
  if (project.image) card.append(renderImage(project));
  const body = element("div", "card-body");
  if (project.image) body.append(element("span", "badge", "Featured"));
  body.append(element("h3", "card-title", project.title));
  if (project.description) body.append(element("p", "card-description", project.description));
  if (project.tags.length) body.append(renderTags(project.tags));
  body.append(renderFooter(project));
  card.append(body);
  return card;
}

// Projects with a screenshot get a full-width card; the rest share a grid below them.
function renderProjects(list, projects) {
  list.append(...projects.filter((project) => project.image).map(renderCard));
  const compact = projects.filter((project) => !project.image);
  if (compact.length === 0) return;
  const grid = element("div", "grid");
  grid.append(...compact.map(renderCard));
  list.append(grid);
}

function renderPortfolio(data) {
  const list = document.getElementById("projects");
  if (!data) {
    list.append(element("p", "message", "No project data found. Run `python3 build.py` to generate it."));
    return;
  }
  const { projects, generated } = data;
  document.getElementById("project-count").textContent = `${projects.length} ${projects.length === 1 ? "project" : "projects"}`;
  document.getElementById("generated").textContent = `Last built ${BUILD_TIME_FORMAT.format(new Date(generated))}`;
  if (projects.length === 0) {
    list.append(element("p", "message", "No projects yet."));
    return;
  }
  renderProjects(list, projects);
}

renderPortfolio(window.PORTFOLIO_DATA);
