"use client"

import * as React from "react"
import { MoreVertical, Edit, PlusCircle, Trash } from "lucide-react"
import { Button } from "@/components/ui/button"

interface NativeMenuProps {
  onEdit: () => void
  onDelete: () => void
  onAddImages: () => void
}

export function NativeMenu({ onEdit, onDelete, onAddImages }: NativeMenuProps) {
  const [open, setOpen] = React.useState(false)
  const menuRef = React.useRef<HTMLDivElement>(null)
  const [hoveredItem, setHoveredItem] = React.useState<string | null>(null)
  
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    
    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])
  
  const handleButtonClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    setOpen(!open)
  }
  
  const menuStyle: React.CSSProperties = {
    position: 'absolute',
    top: '100%',
    right: 0,
    marginTop: '0.25rem',
    width: '12rem',
    borderRadius: '0.375rem',
    border: '1px solid #262626',
    backgroundColor: '#171717',
    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
    zIndex: 9999,
    overflow: 'hidden',
    display: open ? 'block' : 'none'
  }
  
  const getMenuItemStyle = (id: string) => {
    const isHovered = hoveredItem === id
    
    return {
      display: 'flex',
      alignItems: 'center',
      padding: '0.5rem 1rem',
      fontSize: '0.875rem',
      cursor: 'pointer',
      width: '100%',
      textAlign: 'left' as const,
      border: 'none',
      backgroundColor: isHovered ? '#262626' : 'transparent',
      color: id === 'delete' ? (isHovered ? '#f87171' : '#ef4444') : 'inherit',
      transition: 'all 0.15s ease'
    }
  }
  
  return (
    <div className="relative" ref={menuRef}>
      <Button 
        variant="ghost" 
        size="icon" 
        className="h-8 w-8 rounded-full opacity-70 hover:opacity-100"
        onClick={handleButtonClick}
      >
        <MoreVertical className="h-4 w-4" />
      </Button>
      
      <div style={menuStyle}>
        <button
          style={getMenuItemStyle('edit')}
          onMouseEnter={() => setHoveredItem('edit')}
          onMouseLeave={() => setHoveredItem(null)}
          onClick={(e) => {
            e.stopPropagation()
            onEdit()
            setOpen(false)
          }}
        >
          <Edit className="h-4 w-4 mr-2" />
          Edit Folder
        </button>
        <button
          style={getMenuItemStyle('add')}
          onMouseEnter={() => setHoveredItem('add')}
          onMouseLeave={() => setHoveredItem(null)}
          onClick={(e) => {
            e.stopPropagation()
            onAddImages()
            setOpen(false)
          }}
        >
          <PlusCircle className="h-4 w-4 mr-2" />
          Add Images
        </button>
        <button
          style={getMenuItemStyle('delete')}
          onMouseEnter={() => setHoveredItem('delete')}
          onMouseLeave={() => setHoveredItem(null)}
          onClick={(e) => {
            e.stopPropagation()
            onDelete()
            setOpen(false)
          }}
        >
          <Trash className="h-4 w-4 mr-2" />
          Delete Folder
        </button>
      </div>
    </div>
  )
} 