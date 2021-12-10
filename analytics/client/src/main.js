import React from "react";
import ReactDOM from "react-dom";
import { ApolloClient, InMemoryCache, ApolloProvider, } from "@apollo/client";
import { App } from "./App";

const client = new ApolloClient({
    uri: ('graphql_base_url' in window) ? window.graphql_base_url : 'http://api.mocaf.kausal.tech/v1/graphql',
    cache: new InMemoryCache()
});

export function renderToDOM(container) {
  ReactDOM.render((
    <ApolloProvider client={client}>
      <App />
    </ApolloProvider>
  ), container);
}

window.App = {
  renderToDOM,
};
