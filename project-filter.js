const controls = document.querySelector(".project-filters");
const tagButtons = controls.querySelectorAll("[data-tag]");
const cards = document.querySelectorAll(".projects [data-tags]");
const resultCount = document.querySelector(".project-count");

function filterProjects(tag) {
  let count = 0;
  for (const card of cards) {
    card.hidden = Boolean(tag) && !card.dataset.tags.split(" ").includes(tag);
    if (!card.hidden) count++;
  }
  for (const button of tagButtons) {
    button.setAttribute("aria-pressed", String(button.dataset.tag === tag));
  }
  resultCount.textContent = count === 1 ? "1 project" : count + " projects";
}

for (const button of tagButtons) {
  button.addEventListener("click", () => filterProjects(button.dataset.tag));
}
controls.querySelector(".clear-filter").addEventListener("click", () => filterProjects(null));
filterProjects(null);
controls.hidden = false;
