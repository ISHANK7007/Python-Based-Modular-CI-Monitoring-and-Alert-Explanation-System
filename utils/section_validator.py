from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
import re
from enum import Enum

@dataclass
class Section:
    """Represents a GitLab CI log section."""
    name: str
    start_line: int
    end_line: Optional[int] = None
    start_timestamp: float = 0
    end_timestamp: Optional[float] = None
    collapsed: bool = False
    parent: Optional['Section'] = None
    children: List['Section'] = field(default_factory=list)
    validation_issues: List[str] = field(default_factory=list)
    
    @property
    def is_complete(self) -> bool:
        """Check if section has a proper end marker."""
        return self.end_line is not None
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate section duration if complete."""
        if self.end_timestamp and self.start_timestamp:
            return self.end_timestamp - self.start_timestamp
        return None

class ValidationLevel(Enum):
    """Severity levels for section validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

@dataclass
class ValidationIssue:
    """Represents a section validation issue."""
    level: ValidationLevel
    message: str
    section_name: str
    line_number: int
    context: Dict = field(default_factory=dict)

class SectionValidator:
    """Validates and repairs GitLab CI section structures."""
    
    def __init__(self, auto_close_sections: bool = True):
        """Initialize the section validator.
        
        Args:
            auto_close_sections: Whether to automatically close incomplete sections
                                at the end of processing (default: True)
        """
        self.sections: Dict[str, Section] = {}  # All sections by name
        self.active_sections: List[Section] = []  # Stack of currently active sections
        self.root_sections: List[Section] = []  # Top-level sections
        self.validation_issues: List[ValidationIssue] = []
        self.auto_close_sections = auto_close_sections
        
    def start_section(self, name: str, line_number: int, timestamp: float, collapsed: bool = False) -> Section:
        """Register the start of a new section.
        
        Args:
            name: Section name
            line_number: Line number where section starts
            timestamp: Section start timestamp from GitLab annotation
            collapsed: Whether section is collapsed by default
            
        Returns:
            The created Section object
        """
        # Check if section already exists (duplicate start)
        if name in self.sections:
            existing = self.sections[name]
            self._add_validation_issue(
                ValidationLevel.WARNING,
                f"Duplicate section_start for '{name}' (previous at line {existing.start_line})",
                name, line_number, 
                {"previous_line": existing.start_line}
            )
            
            # Update the existing section with the new start if it wasn't properly closed
            if not existing.is_complete:
                existing.start_line = line_number
                existing.start_timestamp = timestamp
                existing.collapsed = collapsed
                return existing
        
        # Create new section
        section = Section(
            name=name,
            start_line=line_number,
            start_timestamp=timestamp,
            collapsed=collapsed
        )
        
        # Register in lookup dictionary
        self.sections[name] = section
        
        # Handle parent-child relationships
        if self.active_sections:
            parent = self.active_sections[-1]
            section.parent = parent
            parent.children.append(section)
        else:
            # Top-level section
            self.root_sections.append(section)
            
        # Add to active sections stack
        self.active_sections.append(section)
        
        return section
    
    def end_section(self, name: str, line_number: int, timestamp: float) -> Optional[Section]:
        """Register the end of a section.
        
        Args:
            name: Section name
            line_number: Line number where section ends
            timestamp: Section end timestamp from GitLab annotation
            
        Returns:
            The closed Section object or None if not found
        """
        # Check if section exists
        if name not in self.sections:
            self._add_validation_issue(
                ValidationLevel.ERROR,
                f"section_end for '{name}' without matching section_start",
                name, line_number
            )
            return None
        
        section = self.sections[name]
        
        # Check if section was already ended
        if section.is_complete:
            self._add_validation_issue(
                ValidationLevel.WARNING,
                f"Duplicate section_end for '{name}' (previously ended at line {section.end_line})",
                name, line_number,
                {"previous_end": section.end_line}
            )
            return section
        
        # Close the section
        section.end_line = line_number
        section.end_timestamp = timestamp
        
        # Validate nesting - sections should be closed in reverse order of opening
        # If we're closing a section that's not at the top of the stack, we have a nesting issue
        if self.active_sections and self.active_sections[-1].name != name:
            # Find position of section in active stack
            try:
                idx = next(i for i, s in enumerate(self.active_sections) if s.name == name)
                # Close all intervening sections automatically
                for i in range(len(self.active_sections) - 1, idx, -1):
                    orphaned = self.active_sections[i]
                    self._auto_close_section(orphaned, line_number)
                    self._add_validation_issue(
                        ValidationLevel.WARNING,
                        f"Auto-closing nested section '{orphaned.name}' due to out-of-order closing",
                        orphaned.name, line_number,
                        {"start_line": orphaned.start_line, "parent": name}
                    )
            except StopIteration:
                self._add_validation_issue(
                    ValidationLevel.ERROR,
                    f"Inconsistent section nesting state for '{name}'",
                    name, line_number
                )
        
        # Update active sections stack
        if self.active_sections and self.active_sections[-1].name == name:
            self.active_sections.pop()
        
        return section
    
    def _auto_close_section(self, section: Section, line_number: int, timestamp: Optional[float] = None) -> None:
        """Automatically close an incomplete section.
        
        Args:
            section: Section to close
            line_number: Line number where section is being closed
            timestamp: Optional timestamp (defaults to current time)
        """
        if section.is_complete:
            return
            
        section.end_line = line_number
        section.end_timestamp = timestamp or section.start_timestamp + 0.001  # Add tiny duration if no timestamp
        
        # Add validation issue
        self._add_validation_issue(
            ValidationLevel.INFO,
            f"Auto-closed incomplete section '{section.name}' (opened at line {section.start_line})",
            section.name, line_number,
            {"start_line": section.start_line}
        )
    
    def _add_validation_issue(self, level: ValidationLevel, message: str, 
                              section_name: str, line_number: int, 
                              context: Dict = None) -> None:
        """Add a validation issue.
        
        Args:
            level: Severity level
            message: Issue description
            section_name: Name of the affected section
            line_number: Line number where issue was detected
            context: Additional context information
        """
        self.validation_issues.append(
            ValidationIssue(
                level=level,
                message=message,
                section_name=section_name,
                line_number=line_number,
                context=context or {}
            )
        )
        
        # If this is for a specific section, also add to its issues list
        if section_name in self.sections:
            section = self.sections[section_name]
            section.validation_issues.append(f"{level.value}: {message}")
    
    def finalize(self, final_line_number: int) -> List[ValidationIssue]:
        """Finalize section validation, auto-closing any incomplete sections.
        
        Args:
            final_line_number: The last line number in the log
            
        Returns:
            List of validation issues
        """
        if self.auto_close_sections:
            # Close any remaining open sections in reverse order
            for section in reversed(self.active_sections):
                self._auto_close_section(section, final_line_number)
            
            # Clear active sections since all are now closed
            self.active_sections.clear()
        
        return self.validation_issues
    
    def get_section_hierarchy(self) -> List[Dict]:
        """Get the complete section hierarchy as a structured dictionary.
        
        Returns:
            List of dictionaries representing the section hierarchy
        """
        def section_to_dict(section: Section) -> Dict:
            return {
                "name": section.name,
                "start_line": section.start_line,
                "end_line": section.end_line,
                "duration": section.duration,
                "collapsed": section.collapsed,
                "complete": section.is_complete,
                "validation_issues": section.validation_issues,
                "children": [section_to_dict(child) for child in section.children]
            }
        
        return [section_to_dict(section) for section in self.root_sections]
    
    def get_section_at_line(self, line_number: int) -> List[Section]:
        """Find all sections that contain the given line number.
        
        Args:
            line_number: Line number to check
            
        Returns:
            List of sections containing the line, from outermost to innermost
        """
        containing_sections = []
        
        for section in self.sections.values():
            end_line = section.end_line or float('inf')
            if section.start_line <= line_number <= end_line:
                containing_sections.append(section)
        
        # Sort by nesting depth (parents first)
        containing_sections.sort(key=lambda s: len(self._get_section_path(s)))
        
        return containing_sections
    
    def _get_section_path(self, section: Section) -> List[str]:
        """Get the full path from root to this section.
        
        Args:
            section: Section to get path for
            
        Returns:
            List of section names from root to this section
        """
        path = []
        current = section
        
        while current:
            path.insert(0, current.name)
            current = current.parent
            
        return path