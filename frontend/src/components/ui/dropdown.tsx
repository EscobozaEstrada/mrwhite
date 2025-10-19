"use client"

import * as React from "react"
import { cn } from "@/lib/utils"

interface DropdownProps {
  children: React.ReactNode
  className?: string
}

interface DropdownTriggerProps {
  children: React.ReactNode
  className?: string
  onClick?: (e: React.MouseEvent) => void
  asChild?: boolean
}

interface DropdownContentProps {
  children: React.ReactNode
  className?: string
  align?: "start" | "end" | "center"
  side?: "top" | "bottom"
}

interface DropdownItemProps {
  children: React.ReactNode
  className?: string
  onClick?: (e: React.MouseEvent) => void
  value?: string
}

export const Dropdown = ({ children, className }: DropdownProps) => {
  const [open, setOpen] = React.useState(false)
  const ref = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }

    document.addEventListener("mousedown", handleClickOutside)
    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
    }
  }, [])

  // Create a context to share the open state and setOpen function
  const DropdownContext = React.createContext<{
    open: boolean;
    setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  }>({
    open,
    setOpen,
  });

  return (
    <DropdownContext.Provider value={{ open, setOpen }}>
      <div ref={ref} className={cn("relative", className)}>
        {React.Children.map(children, (child) => {
          if (React.isValidElement(child)) {
            if (child.type === DropdownTrigger) {
              return React.cloneElement(child as React.ReactElement<DropdownTriggerProps>, {
                onClick: (e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  setOpen(!open)
                  if (child.props.onClick) {
                    child.props.onClick(e)
                  }
                }
              })
            }
            if (child.type === DropdownContent) {
              return open ? React.cloneElement(child as React.ReactElement<DropdownContentProps>, {
                children: React.Children.map(child.props.children, (contentChild) => {
                  if (React.isValidElement(contentChild) && contentChild.type === DropdownItem) {
                    return React.cloneElement(contentChild as React.ReactElement<DropdownItemProps>, {
                      onClick: (e) => {
                        if (contentChild.props.onClick) {
                          contentChild.props.onClick(e)
                        }
                        // Close dropdown after item click
                        setOpen(false)
                      }
                    })
                  }
                  return contentChild
                })
              }) : null
            }
            return child
          }
          return child
        })}
      </div>
    </DropdownContext.Provider>
  )
}

export const DropdownTrigger = ({ children, className, onClick, asChild }: DropdownTriggerProps) => {
  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children, {
      onClick: (e: React.MouseEvent) => {
        if (onClick) onClick(e);
        if (children.props.onClick) children.props.onClick(e);
      },
      className: cn(children.props.className, className)
    });
  }
  
  return (
    <button 
      type="button" 
      className={cn(
        "flex h-10 w-full items-center justify-between rounded-md border border-input bg-white/10 px-3 py-2 text-sm ring-offset-background focus:outline-none focus:border-[var(--mrwhite-primary-color)] focus:ring-1 focus:ring-[var(--mrwhite-primary-color)]",
        className
      )}
      onClick={onClick}
    >
      {children}
    </button>
  )
}

export const DropdownContent = ({ children, className, align = "start", side = "bottom" }: DropdownContentProps) => {
  return (
    <div 
      className={cn(
        "absolute z-50 min-w-[8rem] w-full overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md animate-in fade-in-80",
        "top-[calc(100%+8px)]",
        align === "start" ? "left-0" : align === "end" ? "right-0" : "left-1/2 -translate-x-1/2",
        className
      )}
    >
      <div className="p-1">{children}</div>
    </div>
  )
}

export const DropdownItem = ({ children, className, onClick, value }: DropdownItemProps) => {
  return (
    <button
      type="button"
      className={cn(
        "relative flex w-full cursor-default select-none items-center rounded-sm py-1.5 pl-2 pr-2 text-sm outline-none hover:bg-neutral-800 focus:bg-neutral-800 data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        className
      )}
      onClick={onClick}
      data-value={value}
    >
      {children}
    </button>
  )
}