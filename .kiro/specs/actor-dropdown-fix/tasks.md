# Implementation Plan

- [x] 1. Add debugging to identify the root cause

  - Add console.log statements to track semantic_tag evaluation in questionCard.tsx
  - Verify that questions receive semantic_tag property from backend
  - Check if isCatalog evaluation is working correctly
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Fix the conditional rendering logic

  - Ensure semantic_tag is properly extracted from question data
  - Fix any timing or data structure issues preventing ActorInput from rendering
  - Verify that isActorTag function works with actual data
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 3. Test actor selection functionality

  - Verify that ActorInput component renders for proveedor questions
  - Test that ActorInput component renders for transportista questions
  - Test that ActorInput component renders for receptor questions
  - Confirm search functionality works for each actor type
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2_

- [x] 4. Validate data persistence

  - Test that selected actor data is saved correctly to submission
  - Verify that actor references are maintained in the backend
  - Confirm that previously selected actors display correctly when loading existing submissions
  - _Requirements: 3.2, 3.3, 3.4_

- [x] 5. Handle error cases and edge conditions

  - Implement proper error handling for search failures
  - Add fallback behavior for missing or deleted actors

  - Test behavior when semantic_tag is missing or invalid
  - _Requirements: 2.4, 3.4_
