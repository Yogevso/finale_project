import { describe, expect, it } from 'vitest'

import {
  createInitialContentEditingMachineState,
  toSectionEditTarget,
  transitionContentEditingMachineState,
} from './contentEditingMachine'

describe('contentEditingMachine', () => {
  it('opens chooser and records handled token', () => {
    const initial = createInitialContentEditingMachineState()
    const chooser = transitionContentEditingMachineState(initial, {
      type: 'OPEN_CHOOSER',
      token: 7,
    })

    expect(chooser.phase).toBe('chooser')
    expect(chooser.handledRequestToken).toBe(7)
    expect(chooser.editingSection).toBeNull()
  })

  it('moves from chooser to editing and back', () => {
    const chooser = transitionContentEditingMachineState(
      createInitialContentEditingMachineState(),
      {
        type: 'OPEN_CHOOSER',
        token: 1,
      },
    )

    const editing = transitionContentEditingMachineState(chooser, {
      type: 'START_EDITING',
      section: {
        id: 'section-1',
        text: 'Overview',
        level: 2,
        html: '<h2>Overview</h2>',
        index: 0,
        editMode: 'edit',
      },
    })

    const back = transitionContentEditingMachineState(editing, { type: 'BACK_TO_CHOOSER' })

    expect(editing.phase).toBe('editing')
    expect(editing.editingSection?.text).toBe('Overview')
    expect(back.phase).toBe('chooser')
    expect(back.editingSection).toBeNull()
  })

  it('maps section edit mode based on index when no force mode is provided', () => {
    const fullTarget = toSectionEditTarget({
      id: 'full',
      text: 'Full doc',
      level: 2,
      html: '<p>all</p>',
      index: -1,
    })
    const sectionTarget = toSectionEditTarget({
      id: 's1',
      text: 'Section',
      level: 2,
      html: '<h2>Section</h2>',
      index: 0,
    })

    expect(fullTarget.editMode).toBe('full')
    expect(sectionTarget.editMode).toBe('edit')
  })
})

