* Backend and frontend requirements
* Projects to test
* Fixes from tests

Set of projects that the model should be able to fully implement:

- Backend apis should be fully working:
  - authentication routes
  - all project routes
  - add all packages to requirements.txt
  - redeploy backend when changes
  - shouldnt do 'from backend.xx import x' it should avoid this in order to register all routes
  - always add `__table_args__ = {'extend_existing': True}` for safety
  - `__init__.py` already creates prefix for every route, so dont add any prefixes in each route file (for example, if there is a auth.py then the routes inside of that already have the `auth` prefix. So don't add it in when you are creating the route)

Frontend should be fully integrated with backend and have production app level UI
  - fully integrate the backend APIs with the pages
  - create subcomponents and use them in each page
  - comment out signup/login code if authentication not needed
  - a app should production level UI
    - should have created custom color scheme and css variables
    - sidebar (really nice sidebar is a plus), modals, charts, tables, toasts, ,
    - clean UI design system, minimal padding, rounded corners, fluid and consistent transitoins and animations, visual hierachy, tables for lots of data, showing toasts when relevant, use modals to not clutter the UI, basic haptic feedback, fulfilled UI (build all the UI for the initial requirements and then add finishing touches to app with making it look filled rather than empty with nothing)
    - showing potential next features as UI only
    - should use `sonner` and not `toast` component, shadcn is updated and toast is deprecated
  - all data should be stored on zustand and created handlers to manage the data
  - should properly do integration with understanding of the proepr response formats of the APIs
    - to check if a api call is successful or not it shouldnt be checking for nonexisting proeprties like `res.ok` or `res.success` unless model has verified that the backend returns that proeprty.
    - by default, model should check the status code of the response to determine if the request was successful
  - api errors should be properly handled and shown as sonner component (not toasts)
  - always make sure signup page and login page is integrated with the backend routes, and protected routes logic is properly implemented to redirect user to login page if not authenticated and implement that properly


Basic projects

- Todo app
  - add, edit and delete todos
  - add authentication and show user profile
  - add search functionality
  - share todos with other users

- Project management app
  - full authentication to support multiple users
  - users can create organisation and invite and add other users to the organisation
  - create and manage tasks
  - assign them to people in the organisation
  - manage access to people (some can edit, some can only view)
  - add comments to tasks
  - invited users see organisation view on the app


Changes
  - when a change is requested from the user, make that particular change, but then think how it is connected to the rest of the app and how it will affect the backend and full end to end product workflow itself. for example when you are building project management app, and the user asks to create a onboarding so that when someone signs up it asks them to create a organisation, you make this simple change, but you also think that now each user should now be assigned a organisation from the start they signup, then once they land on the home page the orgnisation info shoudl be saved and it should be showed and it should be part of the app, and everything now should be based on the user and the organisation of the user rather than just the user. you think about all the other touchpoints and all the other connected things that would need to be changed in order to make the product work properly with the given change. [added to prompt]
    - the worst way to do is to just make the change the user wanted and not thinking of how this would affect the rest of the app, backend, frontend and the actual product's workflow from the user's perspective
    - you must make the change the user request, and then think of all these things and ask the user if they want you to make all these changes so that the entire product works properly with the given change and then once they accept do it
  - always use trailing slash in all routes, in backend and frontend. make sure you are consistent in everything. [added to prompt]
  - when handling signup, login must be called to get the token. token must always be stored in zustand and everything in the app must get the token from the zustand store. [added to prompt]
