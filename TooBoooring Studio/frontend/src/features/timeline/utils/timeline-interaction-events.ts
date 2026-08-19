const TIMELINE_MARQUEE_ACTIVE_EVENT = 'tooboooring:timeline-marquee-active'

export function announceTimelineMarqueeActive(active: boolean): void {
  window.dispatchEvent(
    new CustomEvent<{ active: boolean }>(TIMELINE_MARQUEE_ACTIVE_EVENT, {
      detail: { active },
    }),
  )
}
