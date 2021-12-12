import React from "react";
import ReactDOM from "react-dom";
import { ApolloClient, InMemoryCache, ApolloProvider, } from "@apollo/client";
import cubejs from '@cubejs-client/core';
import { CubeProvider } from '@cubejs-client/react';
import numbro from 'numbro';
import { App } from "./App";


let apolloClient;
let cubejsApi;

function initializeApp(container, { graphqlUrl, cubeUrl }) {
  if (!apolloClient) {
    apolloClient = new ApolloClient({
      uri: graphqlUrl || 'https://api.mocaf.kausal.tech/v1/graphql',
      cache: new InMemoryCache()
    });
  }
  if (!cubejsApi) {
    cubejsApi = cubejs('', {
      apiUrl: cubeUrl || 'https://api.mocaf.kausal.tech/cubejs-api/v1',
    });
  }
  numbro.setLanguage('fi');  // FIXME
  ReactDOM.render((
    <ApolloProvider client={apolloClient}>
      <CubeProvider cubejsApi={cubejsApi}>
        <App />
      </CubeProvider>
    </ApolloProvider>
  ), container);
}

window.initializeApp = initializeApp;
