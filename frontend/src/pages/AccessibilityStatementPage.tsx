/**
 * AC-018: Accessibility Statement Page
 */
export default function AccessibilityStatementPage() {
  return (
    <main id="main-content" className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-3xl font-display font-bold text-slate-900 mb-6">
        Accessibility Statement
      </h1>

      <div className="prose prose-slate max-w-none space-y-6">
        <section>
          <h2 className="text-xl font-semibold text-slate-800">Our commitment</h2>
          <p>
            We are committed to ensuring that our platform is accessible to all users,
            including those with disabilities. We aim to conform to the{' '}
            <strong>Web Content Accessibility Guidelines (WCAG) 2.1 Level AA</strong>{' '}
            standard.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-slate-800">Accessibility features</h2>
          <ul className="list-disc pl-6 space-y-2">
            <li>
              <strong>Keyboard navigation</strong> — All interactive elements are reachable
              and operable using a keyboard alone.
            </li>
            <li>
              <strong>Skip navigation</strong> — A "Skip to main content" link is provided
              on every page to bypass repetitive navigation.
            </li>
            <li>
              <strong>Screen reader support</strong> — ARIA landmarks, labels, and live
              regions are used throughout to provide context for assistive technology.
            </li>
            <li>
              <strong>Focus management</strong> — Modal dialogs trap focus, and SPA route
              changes are announced to screen readers.
            </li>
            <li>
              <strong>Color contrast</strong> — Text and interactive elements meet WCAG AA
              contrast ratios (4.5:1 for normal text, 3:1 for large text).
            </li>
            <li>
              <strong>High contrast mode</strong> — The interface supports Windows High
              Contrast and forced-colors media queries.
            </li>
            <li>
              <strong>Form accessibility</strong> — Form fields have explicit labels, and
              validation errors are programmatically associated with their fields.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-slate-800">Known limitations</h2>
          <p>
            While we strive for full compliance, some third-party content (such as
            embedded documents or user-generated HTML) may not fully meet accessibility
            standards. We are continually working to improve these areas.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-slate-800">Feedback</h2>
          <p>
            If you encounter any accessibility barriers while using our platform, please
            contact us. We welcome your feedback and will work to address issues promptly.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-slate-800">Standards</h2>
          <p>
            This platform is evaluated against WCAG 2.1 Level AA using automated tools
            (axe-core, eslint-plugin-jsx-a11y) and manual testing.
          </p>
        </section>
      </div>
    </main>
  )
}
