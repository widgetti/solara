<template>
    <main>
        <section id="hero">
        <nav class="hero-nav"
            style="position: absolute; top: 0; width: 100%; height: 3.5rem; font-size: 1.25rem; font-weight: 300; display: flex; flex-direction: row; justify-content: flex-end; align-items: center; padding: 0 40px; gap: 40px; box-sizing: border-box;">
            <a href="/documentation" style="color: var(--color-text)">
                Documentation
            </a>
            <a href="/showcase" style="color: var(--color-text)">
                Showcase
            </a>
        </nav>
            <div class="hero-stars"></div>
            <div class="hero-planet-element"></div>
            <div class="in-hero-banner">
                Solarathon 2024 • October 13-15 • Last chance to register
            </div>
            <h1>Build high-quality web applications in pure Python</h1>
            <h2>
                From dashboards to large applications: Solara delivers solid, maintainable code trusted by
                startups & large enterprises.
            </h2>
        </section>
        <section id="brand-trust">
            <h3>
                For performance, efficiency and developer experience.
            </h3>
            <h4>
                Solara is trusted by the most innovative teams on the web.
            </h4>
            <div class="logo-grid">
                <a href="https://www.dominodatalab.com/" target="_blank">
                    <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/logos/domino.png" alt="Domino Data Lab"
                        width="80%" />
                </a>
                <a href="https://plotly.com/" target="_blank">
                    <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/logos/plotly.png" alt="Plotly"
                        width="80%" />
                </a>
                <a href="https://merck.com/" target="_blank">
                    <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/logos/merck.svg" alt="Merck" width="80%" />
                </a>
                <a href="https://planeto-energy.ch/" target="_blank">
                    <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/logos/planeto.png" alt="Planeto Energy"
                        width="80%" />
                </a>
            </div>
        </section>
        <section id="modern">
            <h1>Made for modern applications</h1>
            <h4>
                A powerful framework for building high-performance web applications without front-end fuss.
            </h4>
            <div class="modern-element-container card" style="flex-direction: column;">
                <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/lazy-deco-stroke.svg" class="lazy-stroke"
                    width="80%" />
                <h3>
                    Build high-quality web applications without needing front-end experience.
                </h3>
            </div>
            <div class="double-tile-container homepage-row">
                <div class="modern-tile card">
                    <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/solara-card-stack.png" alt="Solara stack"
                        width="100%" />
                    <div class="stack-text-container">
                        <h2>Brings your application to production</h2>
                        <p>
                            Built on a foundation of fast, production-grade tooling. Whether you develop in a Jupyter
                            Notebook
                            or an editor like VScode, Solara brings your application to production.
                        </p>
                    </div>
                </div>
                <div class="modern-tile card">
                    <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/solara-flow-stack.png" alt="Solara stack"
                        width="80%" />
                    <div class="stack-text-container">
                        <h2>Modern API stack supported</h2>
                        <p>
                            Call libraries directly from Python without having to create REST endpoints.
                        </p>
                    </div>
                </div>
            </div>
        </section>
        <section id="features">
            <h1>Every feature you need to build great applications on the web.</h1>
            <h4>Build large applications without exponential complexity.</h4>
            <div class="triple-tile-container homepage-row">
                <div class="feature card">
                    <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/auto-updates.svg" alt="Automatic updates"
                        width="100%" />
                    <div class="stack-text-container">
                        <h2>Fully Automatic Updates</h2>
                        <p>
                            Write your reactive components declaratively and never worry about updating UI, Solara does this
                            automatically, just like a spreadsheet.
                        </p>
                    </div>
                </div>
                <div class="feature card">
                    <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/many-components.svg" alt="Component library"
                        width="100%" />
                    <div class="stack-text-container">
                        <h2>Comprehensive Component Library</h2>
                        <p>
                            Building diverse applications with built-in components; or tailored them to your organization,
                            all within Python.
                        </p>
                    </div>
                </div>
                <div class="feature card double-height">
                    <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/type-safety.svg" alt="Real-time"
                        width="80%" />
                    <div class="stack-text-container">
                        <h2>Type Safety</h2>
                        <p>
                            With Python’s optional typing, type fast and error-free. Spot and fix typing errors directly
                            throughout Solara, from state management to UI components.
                        </p>
                    </div>
                </div>
                <div class="feature card">
                    <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/auto-testing.svg" alt="Automated testing"
                        width="100%" />
                    <div class="stack-text-container">
                        <h2>Fully Testable</h2>
                        <p>
                            Test your applications with and without a browser, from unit tests to end-to-end tests,
                            preferably automated in a CI/CD pipeline. Spot bugs before they hit the user and release with
                            confidence.
                        </p>
                    </div>
                </div>
                <div class="feature card">
                    <div class="stack-text-container">
                        <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/many-frameworks.svg"
                            alt="Framework support" width="100%" />
                        <h2>Compatible with any framework</h2>
                        <p>
                            Ipywidgets, React, Vue, and more - it runs on Solara. Outside Solara’s built-in components
                            within Python, create new frontend components with any framework.
                        </p>
                    </div>
                </div>
            </div>
        </section>
        <section id="choice">
            <h1>The Framework of Choice when it Matters</h1>
            <h4>
                Your team’s toolkit to stop configuring and start innovating. Securely build, deploy, and scale the best web
                experiences with Solara.
            </h4>
            <div class="full-width-slideshow-container">
                <div class="slideshow-column">
                    <div class="piece" style="flex-grow: 1;">
                        <img src="https://dxhl76zpt6fap.cloudfront.net/public/showcase/wanderlust/thumbnail.png"
                            alt="Wanderlust app" />
                    </div>
                    <div class="piece" style="flex-grow: 1;">
                        <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/backgrounds/instagibbs.png"
                            alt="Instagibbs" />
                    </div>
                </div>
                <div class="slideshow-column">
                    <div class="piece" style="flex-grow: 1;">
                        <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/backgrounds/video-analysis.png"
                            alt="Video analysis" />
                    </div>
                </div>
                <div class="slideshow-column">
                    <div class="piece" style="flex-grow: 3;">
                        <img src="https://user-images.githubusercontent.com/1765949/237517090-8f7242b1-3189-4c5b-abd3-0f0986292ade.png"
                            alt="Bulk Labeling" />
                    </div>
                    <div class="slideshow-row" style="flex-grow: 2; height: 0;">
                        <div class="piece" style="flex-grow: 1; height: 100%;">
                            <img src="https://dxhl76zpt6fap.cloudfront.net/public/showcase/solarathon_2023_team_4/thumbnail.png"
                                alt="Live Cryptocurrency Dashboard" />
                        </div>
                        <div class="piece" style="flex-grow: 1; height: 100%;">
                            <img src="https://dxhl76zpt6fap.cloudfront.net/public/showcase/solarathon_2023_team_2/thumbnail.png"
                                alt="Travel Assistant" />
                        </div>
                    </div>
                </div>
                <div class="slideshow-column">
                    <div class="piece" style="flex-grow: 1;">
                        <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/backgrounds/tessa-analysis1.png"
                            alt="District Heating Calculation" />
                    </div>
                    <div class="piece" style="flex-grow: 1;">
                        <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/backgrounds/tessa-analysis2.png"
                            alt="District Heating Calculation" />
                    </div>
                </div>
                <div class="bottom-fade"></div>
            </div>
        </section>
        <section id="cutting-edge">
            <h1>The Home of Cutting-Edge Apps</h1>
            <h4>
                Solara powers you with the full strength of both the Python and Javascript ecosystems.
            </h4>
            <a href="/showcase">
                <button class="cta">See the showcase</button>
            </a>
            <div class="testimonials">
                <div class="testimonial card-flat">
                    <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/logos/plotly.png" alt="Plotly"
                        height="60px" />
                    <p>
                        Solara is like streamlit, but for Jupyter. I am really excited to see where this goes!
                    </p>
                    <div class="testimonial-attribution">
                        <img src="https://dxhl76zpt6fap.cloudfront.net/public/avatar/jack-parmer.jpg" alt="Jack Parmer" />
                        <div style="flex-grow: 1; display: flex; flex-direction: column; justify-content: center;">
                            <h4>Jack Parmer</h4>
                            <p>Former CEO and Co-Founder, Plotly</p>
                        </div>
                    </div>
                </div>
                <div class="testimonial card-flat">
                    <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/logos/planeto.png" alt="Planeto"
                        height="60px" />
                    <p>
                        We evolved our prototype using Solara and are running it in production without needing an expensive
                        rewrite with separate frontend and backend developers.
                    </p>
                    <div class="testimonial-attribution">
                        <img src="https://dxhl76zpt6fap.cloudfront.net/public/avatar/jonathan-chambers.jpg"
                            alt="Jonathan Chambers" />
                        <div style="flex-grow: 1; display: flex; flex-direction: column; justify-content: center;">
                            <h4>Jonathan Chambers</h4>
                            <p>Co-Founder, Planeto Energy</p>
                        </div>
                    </div>
                </div>
                <div class="testimonial card-flat">
                    <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/logos/domino.png" alt="Domino Data Lab"
                        height="60px" />
                    <p>
                        Solara has been transformative, allowing us to rapidly create a Jupyter app and iterate with
                        impressive speed.
                    </p>
                    <div class="testimonial-attribution">
                        <img src="https://dxhl76zpt6fap.cloudfront.net/public/avatar/nick-elprin.jpg" alt="Nick Elprin" />
                        <div style="flex-grow: 1; display: flex; flex-direction: column; justify-content: center;">
                            <h4>Nick Elprin</h4>
                            <p>Co-Founder and CEO, Domino Data Lab</p>
                        </div>
                    </div>
                </div>
            </div>
        </section>
        <section id="learning"
            style="background: radial-gradient(61.25% 47.84% at 50% 0%, rgba(255, 164, 61, 0.06) 0%, rgba(255, 164, 61, 0.00) 100%), radial-gradient(15.33% 28.37% at 50% 42.67%, rgba(255, 164, 61, 0.20) 0%, rgba(255, 164, 61, 0.00) 100%);">
            <div class="top-part">
                <h1>Continue Your Learning Journey</h1>
                <h4>Check out Solara Documentation or subscribe to our newsletter</h4>
                <div id="mc_embed_shell">
                    <div id="mc_embed_signup">
                        <form
                            action="https://gmail.us13.list-manage.com/subscribe/post?u=1dcdd74de47214edace5b6f49&amp;id=c60b5def86&amp;f_id=00f4c1e2f0"
                            method="post" id="mc-embedded-subscribe-form" name="mc-embedded-subscribe-form" class="validate"
                            target="_blank"
                            style="padding: 12px 18px; border-radius: 999px; background: rgba(255, 255, 255, 0.04); backdrop-filter: blur(2px);">
                            <div id="mc_embed_signup_scroll" style="flex-grow: 1;">
                                <div class="mc-field-group">
                                    <input type="email" name="EMAIL" class="required email" id="mce-EMAIL" required=""
                                        value="" placeholder="Enter Your Email">
                                </div>
                                <div class="mc-field-group" style="visibility: hidden; display: none;">
                                    <label for="mce-LOCATION">signup location </label>
                                    <input type="text" name="LOCATION" class=" text" id="mce-LOCATION" value="/">
                                </div>
                                <div id="mce-responses" class="clear foot">
                                    <div class="response" id="mce-error-response" style="display: none;"></div>
                                    <div class="response" id="mce-success-response" style="display: none;"></div>
                                </div>
                                <div aria-hidden="true" style="position: absolute; left: -5000px;">
                                    /* real people should not fill this in and expect good things - do not remove this
                                    or
                                    risk
                                    form bot
                                    signups */
                                    <input type="text" name="b_1dcdd74de47214edace5b6f49_c60b5def86" tabindex="-1" value="">
                                </div>
                            </div>
                            <button type="submit" name="subscribe" id="mc-embedded-subscribe"
                                value="Subscribe">Subscribe</button>
                        </form>
                    </div>
                </div>
            </div>
            <div class="bottom-part">
                <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/mobile-desktop-docs-preview.png"
                    alt="A preview of Solara on Different Devices" width="70%" />
                <div class="bottom-fade"></div>
            </div>
        </section>
        <section id="deploy">
            <div class="card deploy-card">
                <div class="deploy-card-top-text">
                    <h2>Get Started in Seconds</h2>
                    <p>
                        To deploy a new Project, installed Solara as a normal Python package or get started with the server
                        from
                        the command line.
                    </p>
                    <a href="/documentation">
                        Get started &gt;
                    </a>
                </div>
                <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/backgrounds/what-ship.svg"
                    alt="What Will You Ship" width="100%" />
            </div>
            <div class="card deploy-card" style="position: relative; overflow: hidden;">
                <div class="deploy-card-top-text">
                    <h2>Get Support Wherever You Are</h2>
                    <p>
                        We serve developers all across the globe. If you need professional support or consulting, contact us
                        through Widgetti, our parent company.
                    </p>
                    <a href="/contact">
                        Contact Us &gt;
                    </a>
                </div>
                <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/backgrounds/globe.svg"
                    alt="Support Wherever You Are" width="100%" style="position: absolute; bottom: 0; right: 0;" />
            </div>
        </section>
        <section id="ready">
            <h1>Ready to Deploy?</h1>
            <h4>Celebrate the joy of accomplishment with a tool designed to build your app and scale your business.</h4>
            <a href="documentation/getting_started">
                Get Started
            </a>
            <div class="bottom-planet-container">
                <div class="left-fade"></div>
                <div class="right-fade"></div>
                <div class="bottom-fade"></div>
                <div class="bottom-planet-element"></div>
            </div>
        </section>
        <footer>
            <div class="footer-flex homepage-row">
                <div class="footer-flex homepage-column">
                    <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/logos/solara.svg" alt="Solara" width="100px"
                        class="logo" />
                    <div class="footer-flex homepage-column">
                        <a href="https://discord.solara.dev" class="ext-link">
                            <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/logos/discord.svg" alt="Discord"
                                width="20px" style="margin-right: 0.75rem;" />
                            Discord
                        </a>
                        <a href="https://github.com/widgetti/solara" class="ext-link">
                            <img src="https://dxhl76zpt6fap.cloudfront.net/new-homepage/logos/github.svg" alt="GitHub"
                                width="20px" style="margin-right: 0.75rem;" />
                            GitHub
                        </a>
                    </div>
                </div>
                <div class="footer-flex homepage-row" style="width: 40%; padding-right: 60px;">
                    <div class="footer-flex homepage-column">
                        <b>Resources</b>
                        <a href="/pricing">
                            Pricing
                        </a>
                        <a href="/changelog">
                            Changelog
                        </a>
                        <a href="/roadmap">
                            Roadmap
                        </a>
                    </div>
                    <div class="footer-flex homepage-column">
                        <b>Company</b>
                        <a href="/about">
                            About
                        </a>
                        <a href="/our_team">
                            Our Team
                        </a>
                        <a href="/careers">
                            Careers
                        </a>
                    </div>
                    <div class="footer-flex homepage-column">
                        <b>Resources</b>
                        <a href="/documentation">
                            Documentation
                        </a>
                        <a href="/showcase">
                            Showcase
                        </a>
                        <a href="/contact">
                            Contact
                        </a>
                    </div>
                </div>
            </div>
            <div class="footer-flex homepage-row" style="align-items: center;">
                <div>
                    <h2>Join our Developer Newsletter</h2>
                    <h4>Keep up to date with everything Solara, no BS.</h4>
                </div>
                <div id="mc_embed_shell">
                    <div id="mc_embed_signup">
                        <form
                            action="https://gmail.us13.list-manage.com/subscribe/post?u=1dcdd74de47214edace5b6f49&amp;id=c60b5def86&amp;f_id=00f4c1e2f0"
                            method="post" id="mc-embedded-subscribe-form" name="mc-embedded-subscribe-form" class="validate"
                            target="_blank">
                            <div id="mc_embed_signup_scroll" style="flex-grow: 1;">
                                <div class="mc-field-group">
                                    <input type="email" name="EMAIL" class="required email" id="mce-EMAIL" required=""
                                        value="" placeholder="Enter Your Email">
                                </div>
                                <div class="mc-field-group" style="visibility: hidden; display: none;">
                                    <label for="mce-LOCATION">signup location </label>
                                    <input type="text" name="LOCATION" class=" text" id="mce-LOCATION" value="/">
                                </div>
                                <div id="mce-responses" class="clear foot">
                                    <div class="response" id="mce-error-response" style="display: none;"></div>
                                    <div class="response" id="mce-success-response" style="display: none;"></div>
                                </div>
                                <div aria-hidden="true" style="position: absolute; left: -5000px;">
                                    /* real people should not fill this in and expect good things - do not remove this
                                    or
                                    risk
                                    form bot
                                    signups */
                                    <input type="text" name="b_1dcdd74de47214edace5b6f49_c60b5def86" tabindex="-1" value="">
                                </div>
                            </div>
                            <button type="submit" name="subscribe" id="mc-embedded-subscribe"
                                value="Subscribe">Subscribe</button>
                        </form>
                    </div>
                </div>
            </div>
            <div class="footer-flex homepage-row">
                <div>
                    <a>
                        Privacy Policy
                    </a>
                    <a>
                        Terms and Conditions
                    </a>
                </div>
                <small>
                    © 2024 Widgetti BV. All rights reserved.
                </small>
            </div>
        </footer>
    </main>
</template>

<script>

module.exports = {
    async mounted() {
        if (!document.getElementById('homepage.css')) {
            const link = document.createElement('link');
            // link.href = "https://dxhl76zpt6fap.cloudfront.net/new-homepage/styles/main.css";
            link.href = "https://solara-assets.s3.us-east-2.amazonaws.com/new-homepage/styles/main.css";
            link.type = "text/css";
            link.rel = "stylesheet";
            link.id="homepage.css";
            document.head.appendChild(link);
        }
        document.querySelectorAll('a').forEach(this.setupRouter);
    },
    destroyed() {
        // Otherwise we have extra css on other pages after front-end navigation
        document.getElementById('homepage.css').remove();
    },
    methods: {
        setupRouter(a) {
            let href = a.attributes['href'].value;
            if(href.startsWith("./")) {
                // TODO: should we really do this?
                href = location.pathname + href.substr(1);
                a.attributes['href'].href = href;
            }
            let authLink = href.startsWith("/_solara/auth/");
            if( (href.startsWith("./") || href.startsWith("/")) && !authLink) {
                a.onclick = e => {
                    if(href.startsWith("./")) {
                        solara.router.push(href);
                    } else {
                        solara.router.push(href);
                    }
                    e.preventDefault()
                }
            } else if(href.startsWith("#")) {
                href = location.pathname + href;
                a.attributes['href'].value = href;
            }
        },
    },
}
</script>
