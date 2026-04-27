/* ===================== Santos Coy Legacy — main.js ===================== */
(function () {
  if (typeof gsap === "undefined") return;
  gsap.registerPlugin(ScrollTrigger);

  /* ---- Nav scroll state ---- */
  const nav = document.getElementById("topnav");
  const onScroll = () => {
    if (window.scrollY > 40) nav.classList.add("scrolled");
    else nav.classList.remove("scrolled");
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  /* ---- Hero entrance ---- */
  const heroTl = gsap.timeline({ defaults: { ease: "power3.out" } });
  heroTl
    .from(".hero-eyebrow", { opacity: 0, y: 20, duration: 1 })
    .from(".hero-title",   { opacity: 0, y: 40, duration: 1.2 }, "-=0.7")
    .from(".hero-sub",     { opacity: 0, y: 25, duration: 1 },   "-=0.8")
    .from(".hero-rule",    { scaleX: 0, transformOrigin: "center", duration: 0.8 }, "-=0.6")
    .from(".hero-lede",    { opacity: 0, y: 20, duration: 1 },   "-=0.5")
    .from(".hero-cta",     { opacity: 0, y: 15, duration: 0.8 }, "-=0.6")
    .from(".nav-logo, .nav-links li", { opacity: 0, y: -10, duration: 0.6, stagger: 0.06 }, "-=1");

  /* Slow hero parallax */
  gsap.to(".hero-bg img", {
    yPercent: 12,
    ease: "none",
    scrollTrigger: { trigger: ".hero", start: "top top", end: "bottom top", scrub: true }
  });

  /* ---- Generic .reveal fade-up ---- */
  gsap.utils.toArray(".reveal").forEach((el) => {
    gsap.fromTo(
      el,
      { opacity: 0, y: 40 },
      {
        opacity: 1,
        y: 0,
        duration: 1,
        ease: "power3.out",
        scrollTrigger: { trigger: el, start: "top 85%", toggleActions: "play none none reverse" }
      }
    );
  });

  /* ---- Image frames slide-in ---- */
  gsap.utils.toArray(".reveal-img").forEach((el) => {
    gsap.fromTo(
      el,
      { opacity: 0, y: 60, scale: 0.97 },
      {
        opacity: 1,
        y: 0,
        scale: 1,
        duration: 1.3,
        ease: "power3.out",
        scrollTrigger: { trigger: el, start: "top 85%", toggleActions: "play none none reverse" }
      }
    );
  });

  /* ---- Timeline spine grow + entries ---- */
  const spine = document.querySelector(".timeline-spine");
  if (spine) {
    gsap.fromTo(
      spine,
      { scaleY: 0, transformOrigin: "top center" },
      {
        scaleY: 1,
        ease: "none",
        scrollTrigger: {
          trigger: ".timeline",
          start: "top 70%",
          end: "bottom 70%",
          scrub: true
        }
      }
    );
  }

  gsap.utils.toArray(".t-entry").forEach((entry, i) => {
    const isLeft = i % 2 === 0;
    const text = entry.querySelector("div:not(.t-dot)");
    const dot = entry.querySelector(".t-dot");

    if (text) {
      gsap.fromTo(
        text,
        { opacity: 0, x: isLeft ? -60 : 60 },
        {
          opacity: 1,
          x: 0,
          duration: 1,
          ease: "power3.out",
          scrollTrigger: { trigger: entry, start: "top 80%", toggleActions: "play none none reverse" }
        }
      );
    }
    if (dot) {
      gsap.fromTo(
        dot,
        { scale: 0, opacity: 0 },
        {
          scale: 1,
          opacity: 1,
          duration: 0.5,
          ease: "back.out(2)",
          scrollTrigger: { trigger: entry, start: "top 80%", toggleActions: "play none none reverse" }
        }
      );
    }
  });

  /* ---- Smooth anchor offset (account for fixed nav) ---- */
  document.querySelectorAll('a[href^="#"]').forEach((a) => {
    a.addEventListener("click", (e) => {
      const id = a.getAttribute("href");
      if (id.length < 2) return;
      const target = document.querySelector(id);
      if (!target) return;
      e.preventDefault();
      const y = target.getBoundingClientRect().top + window.scrollY - 20;
      window.scrollTo({ top: y, behavior: "smooth" });
    });
  });
})();
