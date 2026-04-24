'use client'

import { useState } from 'react'
import Link from 'next/link'
import { VT323, Cormorant_Garamond } from 'next/font/google'
import { LAB_PROJECTS, type LabProject } from './lab-projects'

const vt323 = VT323({ weight: '400', subsets: ['latin'] })
const cormorant = Cormorant_Garamond({
  weight: ['300', '400'],
  style: ['normal', 'italic'],
  subsets: ['latin'],
  display: 'swap',
})

export default function LabGallery() {
  const [hoveredSlug, setHoveredSlug] = useState<string | null>(null)

  return (
    <div
      className={vt323.className}
      style={{
        minHeight: '100vh',
        backgroundColor: '#080808',
        color: '#e2e2e2',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '3rem 1.5rem',
      }}
    >
      {/* Header */}
      <header style={{ textAlign: 'center', marginBottom: '4rem' }}>
        <h1
          style={{
            fontSize: 'clamp(2.5rem, 6vw, 4rem)',
            letterSpacing: '0.15em',
            marginBottom: '0.75rem',
            background: 'linear-gradient(135deg, #e2e2e2 0%, #888 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          LAB
        </h1>
        <p
          className={cormorant.className}
          style={{
            fontSize: 'clamp(1rem, 2.5vw, 1.25rem)',
            fontStyle: 'italic',
            color: '#666',
            fontWeight: 300,
            maxWidth: '28rem',
          }}
        >
          Experiments in generative art and interactive systems
        </p>
      </header>

      {/* Project grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 340px), 1fr))',
          gap: '1.5rem',
          width: '100%',
          maxWidth: '1100px',
        }}
      >
        {LAB_PROJECTS.map((project) => (
          <ProjectCard
            key={project.slug}
            project={project}
            isHovered={hoveredSlug === project.slug}
            onHover={() => setHoveredSlug(project.slug)}
            onLeave={() => setHoveredSlug(null)}
          />
        ))}
      </div>

      {/* Footer */}
      <footer
        className={cormorant.className}
        style={{
          marginTop: '6rem',
          textAlign: 'center',
          color: '#444',
          fontSize: '0.9rem',
          fontWeight: 300,
        }}
      >
        Made by Sean Ivins
      </footer>
    </div>
  )
}

function ProjectCard({
  project,
  isHovered,
  onHover,
  onLeave,
}: {
  project: LabProject
  isHovered: boolean
  onHover: () => void
  onLeave: () => void
}) {
  const href = project.externalUrl ?? `/lab/${project.slug}`
  const isExternal = !!project.externalUrl

  return (
    <Link
      href={href}
      target={isExternal ? '_blank' : undefined}
      rel={isExternal ? 'noopener noreferrer' : undefined}
      onMouseEnter={onHover}
      onMouseLeave={onLeave}
      style={{
        display: 'block',
        textDecoration: 'none',
        color: 'inherit',
        borderRadius: '12px',
        overflow: 'hidden',
        border: `1px solid ${isHovered ? project.accentColor + '55' : '#1a1a1a'}`,
        transition: 'border-color 0.3s ease, transform 0.3s ease, box-shadow 0.3s ease',
        transform: isHovered ? 'translateY(-4px)' : 'translateY(0)',
        boxShadow: isHovered
          ? `0 12px 40px ${project.accentColor}15, 0 4px 12px rgba(0,0,0,0.5)`
          : '0 2px 8px rgba(0,0,0,0.3)',
        backgroundColor: '#0d0d0d',
      }}
    >
      {/* Gradient preview band */}
      <div
        style={{
          height: '140px',
          background: project.gradient,
          opacity: isHovered ? 1 : 0.8,
          transition: 'opacity 0.3s ease',
          position: 'relative',
        }}
      >
        {/* Project name overlay */}
        <div
          style={{
            position: 'absolute',
            bottom: '12px',
            left: '16px',
            fontSize: '1.75rem',
            letterSpacing: '0.12em',
            textShadow: '0 2px 8px rgba(0,0,0,0.7)',
          }}
        >
          {project.name}
        </div>
        {/* External link badge */}
        {isExternal && (
          <div
            style={{
              position: 'absolute',
              top: '10px',
              right: '10px',
              fontSize: '0.65rem',
              letterSpacing: '0.1em',
              padding: '3px 7px',
              borderRadius: '4px',
              backgroundColor: 'rgba(0,0,0,0.55)',
              color: '#aaa',
              border: '1px solid rgba(255,255,255,0.12)',
            }}
          >
            GITHUB ↗
          </div>
        )}
      </div>

      {/* Card body */}
      <div style={{ padding: '16px 16px 20px' }}>
        <p
          style={{
            fontSize: '0.95rem',
            color: '#999',
            lineHeight: 1.5,
            marginBottom: '12px',
            fontFamily: 'inherit',
          }}
        >
          {project.tagline}
        </p>

        {/* Tech tags */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {project.techTags.map((tag) => (
            <span
              key={tag}
              style={{
                fontSize: '0.7rem',
                letterSpacing: '0.08em',
                padding: '3px 8px',
                borderRadius: '4px',
                backgroundColor: '#161616',
                color: '#666',
                border: '1px solid #222',
              }}
            >
              {tag}
            </span>
          ))}
        </div>
      </div>
    </Link>
  )
}
