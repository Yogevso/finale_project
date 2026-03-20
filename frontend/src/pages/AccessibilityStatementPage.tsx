/**
 * AC-018: Accessibility Statement Page
 */
export default function AccessibilityStatementPage() {
  return (
    <main id="main-content" className="content-shell max-w-4xl animate-fade-in py-12">
      <div className="surface-card space-y-8 rounded-2xl p-8">
        <header className="space-y-2">
          <h1 className="page-title">Accessibility Statement</h1>
          <p className="body-copy">
            Our accessibility commitments, current support, and the standards used to evaluate the platform.
          </p>
        </header>

        <section className="space-y-3">
          <h2 className="section-title">Our commitment</h2>
          <p className="body-copy">
            We are committed to ensuring that our platform is accessible to all users,
            including those with disabilities. We aim to conform to the{' '}
            <strong>Web Content Accessibility Guidelines (WCAG) 2.1 Level AA</strong>{' '}
            standard.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="section-title">Accessibility features</h2>
          <ul className="list-disc space-y-3 pl-6">
            <li className="body-copy">
              <strong>Keyboard navigation</strong> - All interactive elements are reachable
              and operable using a keyboard alone.
            </li>
            <li className="body-copy">
              <strong>Skip navigation</strong> - A "Skip to main content" link is provided
              on every page to bypass repetitive navigation.
            </li>
            <li className="body-copy">
              <strong>Screen reader support</strong> - ARIA landmarks, labels, and live
              regions are used throughout to provide context for assistive technology.
            </li>
            <li className="body-copy">
              <strong>Focus management</strong> - Modal dialogs trap focus, and SPA route
              changes are announced to screen readers.
            </li>
            <li className="body-copy">
              <strong>Color contrast</strong> - Text and interactive elements meet WCAG AA
              contrast ratios (4.5:1 for normal text, 3:1 for large text).
            </li>
            <li className="body-copy">
              <strong>High contrast mode</strong> - The interface supports Windows High
              Contrast and forced-colors media queries.
            </li>
            <li className="body-copy">
              <strong>Form accessibility</strong> - Form fields have explicit labels, and
              validation errors are programmatically associated with their fields.
            </li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="section-title">Known limitations</h2>
          <p className="body-copy">
            While we strive for full compliance, some third-party content, such as
            embedded documents or user-generated HTML, may not fully meet accessibility
            standards. We are continually working to improve these areas.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="section-title">Feedback</h2>
          <p className="body-copy">
            If you encounter any accessibility barriers while using our platform, please
            contact us. We welcome your feedback and will work to address issues promptly.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="section-title">Standards</h2>
          <p className="body-copy">
            This platform is evaluated against WCAG 2.1 Level AA using automated tools
            such as axe-core and eslint-plugin-jsx-a11y, plus manual testing.
          </p>
        </section>
      </div>
    </main>
  )
}
