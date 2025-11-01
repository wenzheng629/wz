#include "moosexApp.h"
#include "Moose.h"
#include "AppFactory.h"
#include "ModulesApp.h"
#include "MooseSyntax.h"

InputParameters
moosexApp::validParams()
{
  InputParameters params = MooseApp::validParams();
  params.set<bool>("use_legacy_material_output") = false;
  params.set<bool>("use_legacy_initial_residual_evaluation_behavior") = false;
  return params;
}

moosexApp::moosexApp(const InputParameters & parameters) : MooseApp(parameters)
{
  moosexApp::registerAll(_factory, _action_factory, _syntax);
}

moosexApp::~moosexApp() {}

void
moosexApp::registerAll(Factory & f, ActionFactory & af, Syntax & syntax)
{
  ModulesApp::registerAllObjects<moosexApp>(f, af, syntax);
  Registry::registerObjectsTo(f, {"moosexApp"});
  Registry::registerActionsTo(af, {"moosexApp"});

  /* register custom execute flags, action syntax, etc. here */
}

void
moosexApp::registerApps()
{
  registerApp(moosexApp);
}

/***************************************************************************************************
 *********************** Dynamic Library Entry Points - DO NOT MODIFY ******************************
 **************************************************************************************************/
extern "C" void
moosexApp__registerAll(Factory & f, ActionFactory & af, Syntax & s)
{
  moosexApp::registerAll(f, af, s);
}
extern "C" void
moosexApp__registerApps()
{
  moosexApp::registerApps();
}
