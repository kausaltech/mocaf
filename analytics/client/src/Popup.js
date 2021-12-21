import React, { useState } from 'react';

export default function Popup ({y, x, children, rel, name}) {
  console.log(y, x, children);
  return <div style={{
                position: 'absolute',
                top: y,
                left: x,
                pointerEvents: 'none',
                backgroundColor: 'white'
              }}>
           <b>{name}</b><br/>
           {rel} %
           {children}
         </div>
}
